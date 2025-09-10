import asyncio
import json
import logging
import os
import signal
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

import websockets
from websockets.server import WebSocketServerProtocol

# Reuse tool implementations directly from the stdio server
# Prefer calling the MCP boundary function to benefit from model resolution, caches, etc.
from server import TOOLS as SERVER_TOOLS  # type: ignore
from server import _ensure_providers_configured  # type: ignore
from server import handle_call_tool as SERVER_HANDLE_CALL_TOOL  # type: ignore

from src.providers.registry import ModelProviderRegistry  # type: ignore
from src.providers.base import ProviderType  # type: ignore

from .session_manager import SessionManager

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("ws_daemon")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())

EXAI_WS_HOST = os.getenv("EXAI_WS_HOST", "127.0.0.1")
EXAI_WS_PORT = int(os.getenv("EXAI_WS_PORT", "8765"))
AUTH_TOKEN = os.getenv("EXAI_WS_TOKEN", "")
MAX_MSG_BYTES = int(os.getenv("EXAI_WS_MAX_BYTES", str(32 * 1024 * 1024)))
PING_INTERVAL = int(os.getenv("EXAI_WS_PING_INTERVAL", "25"))
PING_TIMEOUT = int(os.getenv("EXAI_WS_PING_TIMEOUT", "10"))
CALL_TIMEOUT = int(os.getenv("EXAI_WS_CALL_TIMEOUT", "120"))
HELLO_TIMEOUT = float(os.getenv("EXAI_WS_HELLO_TIMEOUT", "5"))
SESSION_MAX_INFLIGHT = int(os.getenv("EXAI_WS_SESSION_MAX_INFLIGHT", "8"))
GLOBAL_MAX_INFLIGHT = int(os.getenv("EXAI_WS_GLOBAL_MAX_INFLIGHT", "24"))
KIMI_MAX_INFLIGHT = int(os.getenv("EXAI_WS_KIMI_MAX_INFLIGHT", "6"))
GLM_MAX_INFLIGHT = int(os.getenv("EXAI_WS_GLM_MAX_INFLIGHT", "4"))

_metrics_path = LOG_DIR / "ws_daemon.metrics.jsonl"
_health_path = LOG_DIR / "ws_daemon.health.json"

_sessions = SessionManager()
_global_sem = asyncio.BoundedSemaphore(GLOBAL_MAX_INFLIGHT)
_provider_sems: dict[str, asyncio.BoundedSemaphore] = {
    "KIMI": asyncio.BoundedSemaphore(KIMI_MAX_INFLIGHT),
    "GLM": asyncio.BoundedSemaphore(GLM_MAX_INFLIGHT),
}
_shutdown = asyncio.Event()


def _normalize_outputs(outputs: List[Any]) -> List[Dict[str, Any]]:
    norm: List[Dict[str, Any]] = []
    for o in outputs or []:
        try:
            # mcp.types.TextContent has attributes type/text
            t = getattr(o, "type", None) or (o.get("type") if isinstance(o, dict) else None)
            if t == "text":
                text = getattr(o, "text", None) or (o.get("text") if isinstance(o, dict) else None)
                norm.append({"type": "text", "text": text or ""})
            else:
                # Fallback: best-effort stringification
                norm.append({"type": "text", "text": str(o)})
        except Exception:
            norm.append({"type": "text", "text": str(o)})
    return norm


async def _safe_recv(ws: WebSocketServerProtocol, timeout: float):
    try:
        return await asyncio.wait_for(ws.recv(), timeout=timeout)
    except (websockets.exceptions.ConnectionClosedError, ConnectionAbortedError, ConnectionResetError):
        return None
    except asyncio.TimeoutError:
        return None


async def _handle_message(ws: WebSocketServerProtocol, session_id: str, msg: Dict[str, Any]) -> None:
    op = msg.get("op")
    if op == "list_tools":
        # Build a minimal tool descriptor set
        tools = []
        for name, tool in SERVER_TOOLS.items():
            try:
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.get_input_schema(),
                })
            except Exception:
                tools.append({"name": name, "description": getattr(tool, "description", name), "inputSchema": {"type": "object"}})
        await ws.send(json.dumps({"op": "list_tools_res", "tools": tools}))
        return

    if op == "call_tool":
        name = msg.get("name")
        arguments = msg.get("arguments") or {}
        req_id = msg.get("request_id")
        try:
            _ensure_providers_configured()
        except Exception:
            pass
        tool = SERVER_TOOLS.get(name)
        if not tool:
            await ws.send(json.dumps({
                "op": "call_tool_res",
                "request_id": req_id,
                "error": {"code": "TOOL_NOT_FOUND", "message": f"Unknown tool: {name}"}
            }))
            return

        # Determine provider gate based on requested model or defaults
        prov_key = ""
        try:
            model_name = (arguments or {}).get("model")
            if not model_name:
                from config import DEFAULT_MODEL as _DEF_MODEL  # type: ignore
                model_name = _DEF_MODEL
            if model_name:
                # Check which provider advertises this model
                if model_name in set(ModelProviderRegistry.get_available_model_names(provider_type=ProviderType.KIMI)):
                    prov_key = "KIMI"
                elif model_name in set(ModelProviderRegistry.get_available_model_names(provider_type=ProviderType.GLM)):
                    prov_key = "GLM"
        except Exception:
            prov_key = ""

        # Backpressure: try acquire global, provider and per-session slots without waiting
        try:
            await asyncio.wait_for(_global_sem.acquire(), timeout=0.001)
        except asyncio.TimeoutError:
            await ws.send(json.dumps({
                "op": "call_tool_res",
                "request_id": req_id,
                "error": {"code": "OVER_CAPACITY", "message": "Global concurrency limit reached; retry soon"}
            }))
            return
        prov_acquired = False
        if prov_key and prov_key in _provider_sems:
            try:
                await asyncio.wait_for(_provider_sems[prov_key].acquire(), timeout=0.001)
                prov_acquired = True
            except asyncio.TimeoutError:
                await ws.send(json.dumps({
                    "op": "call_tool_res",
                    "request_id": req_id,
                    "error": {"code": "OVER_CAPACITY", "message": f"{prov_key} concurrency limit reached; retry soon"}
                }))
                _global_sem.release()
                return
        acquired_session = False
        try:
            try:
                await asyncio.wait_for((await _sessions.get(session_id)).sem.acquire(), timeout=0.001)  # type: ignore
                acquired_session = True
            except asyncio.TimeoutError:
                await ws.send(json.dumps({
                    "op": "call_tool_res",
                    "request_id": req_id,
                    "error": {"code": "OVER_CAPACITY", "message": "Session concurrency limit reached; retry soon"}
                }))
                return
            start = time.time()
            try:
                outputs = await asyncio.wait_for(
                    SERVER_HANDLE_CALL_TOOL(name, arguments), timeout=CALL_TIMEOUT
                )
                latency = time.time() - start
                try:
                    with _metrics_path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps({
                            "t": time.time(), "op": "call_tool", "lat": latency,
                            "sess": session_id, "name": name, "prov": prov_key or ""
                        }) + "\n")
                except Exception:
                    pass
                await ws.send(json.dumps({
                    "op": "call_tool_res",
                    "request_id": req_id,
                    "outputs": _normalize_outputs(outputs),
                }))
            except asyncio.TimeoutError:
                await ws.send(json.dumps({
                    "op": "call_tool_res",
                    "request_id": req_id,
                    "error": {"code": "TIMEOUT", "message": f"call_tool exceeded {CALL_TIMEOUT}s"}
                }))
            except Exception as e:
                await ws.send(json.dumps({
                    "op": "call_tool_res",
                    "request_id": req_id,
                    "error": {"code": "EXEC_ERROR", "message": str(e)}
                }))
        finally:
            if acquired_session:
                try:
                    (await _sessions.get(session_id)).sem.release()  # type: ignore
                except Exception:
                    pass
            if prov_acquired:
                try:
                    _provider_sems[prov_key].release()
                except Exception:
                    pass
            try:
                _global_sem.release()
            except Exception:
                pass
        return

    if op == "rotate_token":
        old = msg.get("old") or ""
        new = msg.get("new") or ""
        if not old or not new:
            await ws.send(json.dumps({"op": "rotate_token_res", "ok": False, "error": "missing_params"}))
            return
        if AUTH_TOKEN and old != AUTH_TOKEN:
            await ws.send(json.dumps({"op": "rotate_token_res", "ok": False, "error": "unauthorized"}))
            return
        # Update in-memory token
        globals()["AUTH_TOKEN"] = new
        await ws.send(json.dumps({"op": "rotate_token_res", "ok": True}))
        return

    if op == "health":
        # Snapshot basic health
        try:
            sess_ids = await _sessions.list_ids()
        except Exception:
            sess_ids = []
        snapshot = {
            "t": time.time(),
            "sessions": len(sess_ids),
            "global_capacity": GLOBAL_MAX_INFLIGHT,
        }
        await ws.send(json.dumps({"op": "health_res", "ok": True, "health": snapshot}))
        return

    # Unknown op
    await ws.send(json.dumps({"op": "error", "message": f"Unknown op: {op}"}))





async def _serve_connection(ws: WebSocketServerProtocol) -> None:
    # Expect hello first with timeout, handle abrupt client disconnects gracefully
    hello_raw = await _safe_recv(ws, timeout=HELLO_TIMEOUT)
    if not hello_raw:
        # Client connected but did not send hello or disconnected; close quietly
        try:
            await ws.close(code=4002, reason="hello timeout or disconnect")
        except Exception:
            pass
        return


    try:
        hello = json.loads(hello_raw)
    except Exception:
        try:
            await ws.send(json.dumps({"op": "hello_ack", "ok": False, "error": "invalid_hello"}))
            await ws.close(code=4000, reason="invalid hello")
        except Exception:
            pass
        return

    if hello.get("op") != "hello":
        try:
            await ws.send(json.dumps({"op": "hello_ack", "ok": False, "error": "missing_hello"}))
            await ws.close(code=4001, reason="missing hello")
        except Exception:
            pass
        return

    token = hello.get("token", "")
    if AUTH_TOKEN and token != AUTH_TOKEN:
        try:
            await ws.send(json.dumps({"op": "hello_ack", "ok": False, "error": "unauthorized"}))
            await ws.close(code=4003, reason="unauthorized")
        except Exception:
            pass
        return

    # Always assign a fresh daemon-side session id for isolation
    session_id = str(uuid.uuid4())
    sess = await _sessions.ensure(session_id)
    try:
        await ws.send(json.dumps({"op": "hello_ack", "ok": True, "session_id": sess.session_id}))
    except (websockets.exceptions.ConnectionClosedError, ConnectionAbortedError, ConnectionResetError):
        # Client closed during hello ack; just return
        return

    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except Exception:
                # Try to inform client; ignore if already closed
                try:
                    await ws.send(json.dumps({"op": "error", "message": "invalid_json"}))
                except Exception:
                    pass
                continue
            try:
                await _handle_message(ws, sess.session_id, msg)
            except (websockets.exceptions.ConnectionClosedError, ConnectionAbortedError, ConnectionResetError):
                # Client disconnected mid-processing; exit loop
                break
    except (websockets.exceptions.ConnectionClosedError, ConnectionAbortedError, ConnectionResetError):
        # Iterator may raise on abrupt close; treat as normal disconnect
        pass
    finally:
        try:
            await _sessions.remove(sess.session_id)
        except Exception:
            pass


async def _health_writer(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            sess_ids = await _sessions.list_ids()
        except Exception:
            sess_ids = []
        # Approximate inflight via semaphore value
        try:
            inflight_global = GLOBAL_MAX_INFLIGHT - _global_sem._value  # type: ignore[attr-defined]
        except Exception:
            inflight_global = None
        snapshot = {
            "t": time.time(),
            "sessions": len(sess_ids),
            "global_capacity": GLOBAL_MAX_INFLIGHT,
            "global_inflight": inflight_global,
        }
        try:
            _health_path.write_text(json.dumps(snapshot), encoding="utf-8")
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            continue


async def main_async() -> None:
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal(*_args):
        stop_event.set()

    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, _signal)
        except NotImplementedError:
            # Windows may not support signal handlers in some environments
            pass

    logger.info(f"Starting WS daemon on ws://{EXAI_WS_HOST}:{EXAI_WS_PORT}")
    async with websockets.serve(
        _serve_connection,
        EXAI_WS_HOST,
        EXAI_WS_PORT,
        max_size=MAX_MSG_BYTES,
        ping_interval=PING_INTERVAL,
        ping_timeout=PING_TIMEOUT,
        close_timeout=1.0,
    ):
        # Start health writer
        asyncio.create_task(_health_writer(stop_event))
        # Wait indefinitely until a signal or external shutdown sets the event
        await stop_event.wait()


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

