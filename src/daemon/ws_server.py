import asyncio
import json
import logging
import os
import signal
import time
import uuid
from pathlib import Path
import socket

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
PING_INTERVAL = int(os.getenv("EXAI_WS_PING_INTERVAL", "45"))  # wider interval to reduce false timeouts
PING_TIMEOUT = int(os.getenv("EXAI_WS_PING_TIMEOUT", "30"))    # allow slower systems to respond to pings
CALL_TIMEOUT = int(os.getenv("EXAI_WS_CALL_TIMEOUT", "300"))  # default 5m to align with expert analysis
HELLO_TIMEOUT = float(os.getenv("EXAI_WS_HELLO_TIMEOUT", "15"))  # allow slower clients to hello
# Heartbeat cadence while tools run; keep <10s to satisfy clients with 10s idle cutoff
PROGRESS_INTERVAL = float(os.getenv("EXAI_WS_PROGRESS_INTERVAL_SECS", "8.0"))
SESSION_MAX_INFLIGHT = int(os.getenv("EXAI_WS_SESSION_MAX_INFLIGHT", "8"))
GLOBAL_MAX_INFLIGHT = int(os.getenv("EXAI_WS_GLOBAL_MAX_INFLIGHT", "24"))
KIMI_MAX_INFLIGHT = int(os.getenv("EXAI_WS_KIMI_MAX_INFLIGHT", "6"))
GLM_MAX_INFLIGHT = int(os.getenv("EXAI_WS_GLM_MAX_INFLIGHT", "4"))

_metrics_path = LOG_DIR / "ws_daemon.metrics.jsonl"
_health_path = LOG_DIR / "ws_daemon.health.json"

PID_FILE = LOG_DIR / "ws_daemon.pid"
STARTED_AT: float | None = None


def _create_pidfile() -> bool:
    """Create an exclusive PID file. Returns True if created, False if already exists.
    If a stale file exists (e.g., after a crash), we leave it in place for now and
    rely on bind attempt and health probe to decide how to proceed.
    """
    try:
        # Exclusive create
        with open(PID_FILE, "x", encoding="utf-8") as f:
            f.write(str(os.getpid()))
        return True
    except FileExistsError:
        return False
    except Exception:
        # Do not fail daemon start purely due to pidfile problems
        return True


def _remove_pidfile() -> None:
    try:
        if PID_FILE.exists():
            PID_FILE.unlink(missing_ok=True)  # type: ignore[arg-type]
    except Exception:
        pass

def _is_port_listening(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.25):
            return True
    except Exception:
        return False


def _is_health_fresh(max_age_s: float = 20.0) -> bool:
    try:
        if not _health_path.exists():
            return False
        data = json.loads(_health_path.read_text(encoding="utf-8"))
        t = float(data.get("t") or 0)
        return (time.time() - t) <= max_age_s
    except Exception:
        return False

_sessions = SessionManager()
_global_sem = asyncio.BoundedSemaphore(GLOBAL_MAX_INFLIGHT)
_provider_sems: dict[str, asyncio.BoundedSemaphore] = {
    "KIMI": asyncio.BoundedSemaphore(KIMI_MAX_INFLIGHT),
    "GLM": asyncio.BoundedSemaphore(GLM_MAX_INFLIGHT),
}
# Track in-flight calls by semantic call key so duplicate calls can await the same result
_inflight_by_key: dict[str, asyncio.Event] = {}

_shutdown = asyncio.Event()
RESULT_TTL_SECS = int(os.getenv("EXAI_WS_RESULT_TTL", "600"))
_results_cache: dict[str, dict] = {}
# Cache by semantic call key (tool name + normalized arguments) to survive req_id changes across reconnects
_results_cache_by_key: dict[str, dict] = {}
_inflight_reqs: set[str] = set()


def _gc_results_cache() -> None:
    try:
        now = time.time()
        expired = [rid for rid, rec in _results_cache.items() if now - rec.get("t", 0) > RESULT_TTL_SECS]
        for rid in expired:
            _results_cache.pop(rid, None)
        expired_keys = [k for k, rec in _results_cache_by_key.items() if now - rec.get("t", 0) > RESULT_TTL_SECS]
        for k in expired_keys:
            _results_cache_by_key.pop(k, None)
    except Exception:
        pass


def _store_result(req_id: str, payload: dict) -> None:
    _results_cache[req_id] = {"t": time.time(), "payload": payload}
    _gc_results_cache()


def _get_cached_result(req_id: str) -> dict | None:
    rec = _results_cache.get(req_id)
    if not rec:
        return None
    if time.time() - rec.get("t", 0) > RESULT_TTL_SECS:
        _results_cache.pop(req_id, None)
        return None
    return rec.get("payload")


def _make_call_key(name: str, arguments: dict) -> str:
    try:
        # Stable JSON key for arguments (already JSON-serializable from client)
        key_obj = {"name": name, "arguments": arguments}
        return json.dumps(key_obj, sort_keys=True, separators=(",", ":"))
    except Exception:
        # Fallback: best-effort string
        return f"{name}:{str(arguments)}"


def _store_result_by_key(call_key: str, outputs: list[dict]) -> None:
    _results_cache_by_key[call_key] = {"t": time.time(), "outputs": outputs}
    _gc_results_cache()


def _get_cached_by_key(call_key: str) -> list[dict] | None:
    rec = _results_cache_by_key.get(call_key)
    if not rec:
        return None
    if time.time() - rec.get("t", 0) > RESULT_TTL_SECS:
        _results_cache_by_key.pop(call_key, None)
        return None
    return rec.get("outputs")



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


async def _safe_send(ws: WebSocketServerProtocol, payload: dict) -> bool:
    """Best-effort send that swallows disconnects and logs at debug level.

    Returns False if the connection is closed or an error occurred, True on success.
    """
    try:
        await ws.send(json.dumps(payload))
        return True
    except (
        websockets.exceptions.ConnectionClosedOK,
        websockets.exceptions.ConnectionClosedError,
        ConnectionAbortedError,
        ConnectionResetError,
    ):
        # Normal disconnect during send; treat as benign
        logger.debug("_safe_send: connection closed while sending %s", payload.get("op"))
        return False
    except Exception as e:
        logger.debug("_safe_send: unexpected send error: %s", e)
        return False


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
        await _safe_send(ws, {"op": "list_tools_res", "tools": tools})
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
            await _safe_send(ws, {
                "op": "call_tool_res",
                "request_id": req_id,
                "error": {"code": "TOOL_NOT_FOUND", "message": f"Unknown tool: {name}"}
            })
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
        # Fast-path duplicate handling: if client retries with same req_id, serve result or inform inflight
        cached = _get_cached_result(req_id)
        if cached:
            await _safe_send(ws, cached)
            return
        # Semantic de-duplication: if client reconnects and reissues the same call with a new req_id, serve cached outputs
        call_key = _make_call_key(name, arguments)
        # Optional: disable semantic coalescing per tool via env EXAI_WS_DISABLE_COALESCE_FOR_TOOLS
        try:
            _disable_set = {s.strip().lower() for s in os.getenv("EXAI_WS_DISABLE_COALESCE_FOR_TOOLS", "").split(",") if s.strip()}
        except Exception:
            _disable_set = set()
        if name.lower() in _disable_set:
            # Make call_key unique to avoid coalescing for this tool
            call_key = f"{call_key}::{uuid.uuid4()}"
        cached_outputs = _get_cached_by_key(call_key)
        if cached_outputs is not None:
            payload = {"op": "call_tool_res", "request_id": req_id, "outputs": cached_outputs}
            await _safe_send(ws, payload)
            _store_result(req_id, payload)
            return
        if req_id in _inflight_reqs:
            await _safe_send(ws, {"op": "progress", "request_id": req_id, "name": name, "t": time.time(), "note": "duplicate request; still processing"})
            return

        # Coalesce duplicate semantic calls across reconnects: if another call with the same call_key is in-flight,
        # wait for it to finish and serve its cached outputs instead of launching a second provider call.
        if call_key in _inflight_by_key:
            try:
                await asyncio.wait_for(_inflight_by_key[call_key].wait(), timeout=CALL_TIMEOUT)
                cached_outputs = _get_cached_by_key(call_key)
                if cached_outputs is not None:
                    payload = {"op": "call_tool_res", "request_id": req_id, "outputs": cached_outputs}
                    await _safe_send(ws, payload)
                    _store_result(req_id, payload)
                    return
            except asyncio.TimeoutError:
                await _safe_send(ws, {
                    "op": "call_tool_res",
                    "request_id": req_id,
                    "error": {"code": "TIMEOUT", "message": f"duplicate call_key timed out after {CALL_TIMEOUT}s"}
                })
                return
        else:
            _inflight_by_key[call_key] = asyncio.Event()


        try:
            await asyncio.wait_for(_global_sem.acquire(), timeout=0.001)
        except asyncio.TimeoutError:
            await _safe_send(ws, {
                "op": "call_tool_res",
                "request_id": req_id,
                "error": {"code": "OVER_CAPACITY", "message": "Global concurrency limit reached; retry soon"}
            })
            return
        # Defer ACK until after provider+session capacity to ensure a single ACK per request
        # Also emit an immediate progress breadcrumb so clients see activity right away
        await _safe_send(ws, {
            "op": "progress",
            "request_id": req_id,
            "name": name,
            "t": time.time(),
            "note": "accepted, awaiting provider/session capacity"
        })

        prov_acquired = False
        if prov_key and prov_key in _provider_sems:
            try:
                await asyncio.wait_for(_provider_sems[prov_key].acquire(), timeout=0.001)
                prov_acquired = True
            except asyncio.TimeoutError:
                await _safe_send(ws, {
                    "op": "call_tool_res",
                    "request_id": req_id,
                    "error": {"code": "OVER_CAPACITY", "message": f"{prov_key} concurrency limit reached; retry soon"}
                })
                _global_sem.release()
                return
            # Defer ACK; will send once after session acquisition to guarantee a single ACK

        acquired_session = False
        try:
            try:
                await asyncio.wait_for((await _sessions.get(session_id)).sem.acquire(), timeout=0.001)  # type: ignore
                acquired_session = True
            except asyncio.TimeoutError:
                await _safe_send(ws, {
                    "op": "call_tool_res",
                    "request_id": req_id,
                    "error": {"code": "OVER_CAPACITY", "message": "Session concurrency limit reached; retry soon"}
                })
                return
            start = time.time()
            # Single ACK after global+provider+session acquisition
            await _safe_send(ws, {
                "op": "call_tool_ack",
                "request_id": req_id,
                "accepted": True,
                "timeout": CALL_TIMEOUT,
                "name": name,
            })

            # Inject session and call_key into arguments for provider-side idempotency and context cache
            try:
                arguments = dict(arguments)
                arguments.setdefault("_session_id", session_id)
                arguments.setdefault("_call_key", call_key)
            except Exception:
                pass

            _inflight_reqs.add(req_id)
            try:
                # Emit periodic progress while tool runs
                # Compute a hard deadline for this tool invocation
                tool_timeout = CALL_TIMEOUT
                try:
                    if name == "kimi_chat_with_tools":
                        # Short timeout for normal chat; longer for web-enabled runs
                        _kimitt = float(os.getenv("KIMI_CHAT_TOOL_TIMEOUT_SECS", "180"))
                        _kimiweb = float(os.getenv("KIMI_CHAT_TOOL_TIMEOUT_WEB_SECS", "300"))
                        # arguments is a dict we pass into the tool below; check websearch flag if present
                        use_web = False
                        try:
                            use_web = bool(arguments.get("use_websearch"))
                        except Exception:
                            use_web = False
                        if use_web:
                            # For web-enabled calls, allow the higher web timeout explicitly
                            tool_timeout = int(_kimiweb)
                        else:
                            tool_timeout = min(tool_timeout, int(_kimitt))
                except Exception:
                    pass
                deadline = start + float(tool_timeout)

                tool_task = asyncio.create_task(SERVER_HANDLE_CALL_TOOL(name, arguments))
                while True:
                    try:
                        outputs = await asyncio.wait_for(tool_task, timeout=PROGRESS_INTERVAL)
                        break
                    except asyncio.TimeoutError:
                        # Heartbeat progress to client
                        await _safe_send(ws, {
                            "op": "progress",
                            "request_id": req_id,
                            "name": name,
                            "t": time.time(),
                        })
                        # Enforce hard deadline
                        if time.time() >= deadline:
                            try:
                                tool_task.cancel()
                            except Exception:
                                pass
                            await _safe_send(ws, {
                                "op": "call_tool_res",
                                "request_id": req_id,
                                "error": {"code": "TIMEOUT", "message": f"call_tool exceeded {tool_timeout}s"}
                            })
                            try:
                                if call_key in _inflight_by_key:
                                    _inflight_by_key[call_key].set()
                                    _inflight_by_key.pop(call_key, None)
                            except Exception:
                                pass
                            return
                latency = time.time() - start
                try:
                    with _metrics_path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps({
                            "t": time.time(), "op": "call_tool", "lat": latency,
                            "sess": session_id, "name": name, "prov": prov_key or ""
                        }) + "\n")
                except Exception:
                    pass
                outputs_norm = _normalize_outputs(outputs)
                result_payload = {
                    "op": "call_tool_res",
                    "request_id": req_id,
                    "outputs": outputs_norm,
                }
                await _safe_send(ws, result_payload)
                _store_result(req_id, result_payload)
                # Store by semantic call key to allow delivery across reconnects with new req_id
                try:
                    _store_result_by_key(call_key, outputs_norm)
                    # Signal any duplicate waiters on this call_key
                    if call_key in _inflight_by_key:
                        _inflight_by_key[call_key].set()
                        _inflight_by_key.pop(call_key, None)
                except Exception:
                    pass
            except asyncio.TimeoutError:
                await _safe_send(ws, {
                    "op": "call_tool_res",
                    "request_id": req_id,
                    "error": {"code": "TIMEOUT", "message": f"call_tool exceeded {CALL_TIMEOUT}s"}
                })
                try:
                    if call_key in _inflight_by_key:
                        _inflight_by_key[call_key].set()
                        _inflight_by_key.pop(call_key, None)
                except Exception:
                    pass
            except Exception as e:
                await _safe_send(ws, {
                    "op": "call_tool_res",
                    "request_id": req_id,
                    "error": {"code": "EXEC_ERROR", "message": str(e)}
                })
                try:
                    if call_key in _inflight_by_key:
                        _inflight_by_key[call_key].set()
                        _inflight_by_key.pop(call_key, None)
                except Exception:
                    pass
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
            await _safe_send(ws, {"op": "rotate_token_res", "ok": False, "error": "missing_params"})
            return
        if AUTH_TOKEN and old != AUTH_TOKEN:
            await _safe_send(ws, {"op": "rotate_token_res", "ok": False, "error": "unauthorized"})
            return
        # Update in-memory token
        globals()["AUTH_TOKEN"] = new
        await _safe_send(ws, {"op": "rotate_token_res", "ok": True})
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
        await _safe_send(ws, {"op": "health_res", "ok": True, "health": snapshot})
        return

    # Unknown op
    await _safe_send(ws, {"op": "error", "message": f"Unknown op: {op}"})





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
            await _safe_send(ws, {"op": "hello_ack", "ok": False, "error": "invalid_hello"})
            try:
                await ws.close(code=4000, reason="invalid hello")
            except Exception:
                pass
        except Exception:
            pass
        return

    if hello.get("op") != "hello":
        try:
            await _safe_send(ws, {"op": "hello_ack", "ok": False, "error": "missing_hello"})
            try:
                await ws.close(code=4001, reason="missing hello")
            except Exception:
                pass
        except Exception:
            pass
        return

    token = hello.get("token", "")
    if AUTH_TOKEN and token != AUTH_TOKEN:
        try:
            await _safe_send(ws, {"op": "hello_ack", "ok": False, "error": "unauthorized"})
            try:
                await ws.close(code=4003, reason="unauthorized")
            except Exception:
                pass
        except Exception:
            pass
        return

    # Always assign a fresh daemon-side session id for isolation
    session_id = str(uuid.uuid4())
    sess = await _sessions.ensure(session_id)
    try:
        ok = await _safe_send(ws, {"op": "hello_ack", "ok": True, "session_id": sess.session_id})
        if not ok:
            return
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
                    await _safe_send(ws, {"op": "error", "message": "invalid_json"})
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
            "pid": os.getpid(),
            "host": EXAI_WS_HOST,
            "port": EXAI_WS_PORT,
            "started_at": STARTED_AT,
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
    global STARTED_AT
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

    # Best-effort single-instance guard with stale lock auto-clear
    if not _create_pidfile():
        # If PID file exists but no one is listening OR health is stale, clear it
        if (not _is_port_listening(EXAI_WS_HOST, EXAI_WS_PORT)) or (not _is_health_fresh()):
            logger.warning("Stale PID file or no active listener detected; removing %s", PID_FILE)
            _remove_pidfile()
            if not _create_pidfile():
                logger.error("Unable to recreate PID file after clearing stale lock. Exiting.")
                return
        else:
            logger.warning(
                "PID file exists at %s - another WS daemon may already be running. If you recently crashed or rebooted, "
                "verify with logs/ws_daemon.health.json or check port %s. Exiting.",
                PID_FILE,
                EXAI_WS_PORT,
            )
            return

    STARTED_AT = time.time()

    logger.info(f"Starting WS daemon on ws://{EXAI_WS_HOST}:{EXAI_WS_PORT}")
    try:
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
    except OSError as e:
        # Friendly message on address-in-use
        if getattr(e, "errno", None) in (98, 10048):  # 98=EADDRINUSE (POSIX), 10048=WSAEADDRINUSE (Windows)
            logger.error(
                "Address already in use: ws://%s:%s. A daemon is likely already running. "
                "Use scripts/run_ws_shim.py to connect, or stop the existing daemon. See logs/mcp_server.log and logs/ws_daemon.health.json.",
                EXAI_WS_HOST,
                EXAI_WS_PORT,
            )
            return
        raise
    finally:
        _remove_pidfile()


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

