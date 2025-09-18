#!/usr/bin/env python
import asyncio
import json
import logging
import os
import sys
import uuid
from typing import Any, Dict, List

from pathlib import Path
# Ensure repository root is on sys.path
_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Load environment from .env if available (unify with classic). ENV_FILE overrides.
try:
    from dotenv import load_dotenv  # type: ignore
    _explicit_env = os.getenv("ENV_FILE")
    _env_path = _explicit_env if (_explicit_env and os.path.exists(_explicit_env)) else str(_repo_root / ".env")
    load_dotenv(dotenv_path=_env_path)
except Exception:
    pass

import websockets
from mcp.server import Server
from mcp.types import Tool, TextContent

from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, stream=sys.stderr)
logger = logging.getLogger("ws_shim")
logger.debug(f"EX WS Shim starting pid={os.getpid()} py={sys.executable} repo={_repo_root}")

# Add file logging to capture shim startup/errors regardless of host client
try:
    _logs_dir = _repo_root / "logs"
    _logs_dir.mkdir(parents=True, exist_ok=True)
    _fh = logging.FileHandler(str(_logs_dir / "ws_shim.log"), encoding="utf-8")
    _fh.setLevel(LOG_LEVEL)
    _fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(_fh)
    logger.debug("File logging enabled at logs/ws_shim.log")
except Exception:
    # Never let logging setup break the shim
    pass

EXAI_WS_HOST = os.getenv("EXAI_WS_HOST", "127.0.0.1")
EXAI_WS_PORT = int(os.getenv("EXAI_WS_PORT", "8765"))
EXAI_WS_TOKEN = os.getenv("EXAI_WS_TOKEN", "")
SESSION_ID = os.getenv("EXAI_SESSION_ID", str(uuid.uuid4()))
MAX_MSG_BYTES = int(os.getenv("EXAI_WS_MAX_BYTES", str(32 * 1024 * 1024)))
PING_INTERVAL = int(os.getenv("EXAI_WS_PING_INTERVAL", "45"))
PING_TIMEOUT = int(os.getenv("EXAI_WS_PING_TIMEOUT", "30"))
EXAI_WS_AUTOSTART = os.getenv("EXAI_WS_AUTOSTART", "true").strip().lower() == "true"
EXAI_WS_CONNECT_TIMEOUT = float(os.getenv("EXAI_WS_CONNECT_TIMEOUT", "30"))
EXAI_WS_HANDSHAKE_TIMEOUT = float(os.getenv("EXAI_WS_HANDSHAKE_TIMEOUT", "15"))
EXAI_SHIM_ACK_GRACE_SECS = float(os.getenv("EXAI_SHIM_ACK_GRACE_SECS", "120"))

server = Server(os.getenv("MCP_SERVER_ID", "ex-ws-shim"))

_ws = None  # type: ignore
_ws_lock = asyncio.Lock()


async def _start_daemon_if_configured() -> None:
    if not EXAI_WS_AUTOSTART:
        return
    try:
        # Launch the daemon in the same venv Python, non-blocking
        py = sys.executable
        daemon = str(_repo_root / "scripts" / "run_ws_daemon.py")
        logger.info(f"Autostarting WS daemon: {py} -u {daemon}")
        # Use CREATE_NEW_PROCESS_GROUP on Windows implicitly via asyncio
        await asyncio.create_subprocess_exec(py, "-u", daemon, cwd=str(_repo_root))
    except Exception as e:
        logger.warning(f"Failed to autostart WS daemon: {e}")


async def _ensure_ws():
    global _ws
    if _ws and not _ws.closed:
        return _ws
    async with _ws_lock:
        if _ws and not _ws.closed:
            return _ws
        uri = f"ws://{EXAI_WS_HOST}:{EXAI_WS_PORT}"
        deadline = asyncio.get_running_loop().time() + EXAI_WS_CONNECT_TIMEOUT
        autostart_attempted = False
        last_err: Exception | None = None
        backoff = 0.25
        while True:
            try:
                # Allow disabling pings by setting EXAI_WS_PING_INTERVAL=0
                _pi = None if PING_INTERVAL <= 0 else PING_INTERVAL
                _pt = None if _pi is None or PING_TIMEOUT <= 0 else PING_TIMEOUT
                _ws = await websockets.connect(
                    uri,
                    max_size=MAX_MSG_BYTES,
                    ping_interval=_pi,
                    ping_timeout=_pt,
                    open_timeout=EXAI_WS_HANDSHAKE_TIMEOUT,
                )
                # Hello handshake
                await _ws.send(json.dumps({
                    "op": "hello",
                    "session_id": SESSION_ID,
                    "token": EXAI_WS_TOKEN,
                }))
                # Wait for ack with a handshake timeout window independent of connect
                ack_raw = await asyncio.wait_for(_ws.recv(), timeout=EXAI_WS_HANDSHAKE_TIMEOUT)
                ack = json.loads(ack_raw)
                if not ack.get("ok"):
                    raise RuntimeError(f"WS daemon refused connection: {ack}")
                return _ws
            except Exception as e:
                last_err = e
                # Try autostart once if refused
                if not autostart_attempted:
                    autostart_attempted = True
                    await _start_daemon_if_configured()
                # Check deadline
                if asyncio.get_running_loop().time() >= deadline:
                    break
                # Exponential backoff with cap ~2s
                await asyncio.sleep(backoff)
                backoff = min(2.0, backoff * 1.5)
        # If we reach here, we failed to connect within timeout
        raise RuntimeError(f"Failed to connect to WS daemon at {uri} within {EXAI_WS_CONNECT_TIMEOUT}s: {last_err}")


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    ws = await _ensure_ws()
    await ws.send(json.dumps({"op": "list_tools"}))
    raw = await ws.recv()
    msg = json.loads(raw)
    if msg.get("op") != "list_tools_res":
        raise RuntimeError(f"Unexpected reply from daemon: {msg}")
    tools = []
    for t in msg.get("tools", []):
        tools.append(Tool(name=t.get("name"), description=t.get("description"), inputSchema=t.get("inputSchema") or {"type": "object"}))
    return tools


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    async def _once() -> List[TextContent]:
        ws = await _ensure_ws()
        req_id = str(uuid.uuid4())
        await ws.send(json.dumps({
            "op": "call_tool",
            "request_id": req_id,
            "name": name,
            "arguments": arguments or {},
        }))
        # Read until matching request_id with timeout
        timeout_s = float(os.getenv("EXAI_SHIM_RPC_TIMEOUT", "300"))
        ack_grace = float(os.getenv("EXAI_SHIM_ACK_GRACE_SECS", "30"))
        deadline = asyncio.get_running_loop().time() + timeout_s
        while True:
            remaining = max(0.1, deadline - asyncio.get_running_loop().time())
            try:
                raw = await asyncio.wait_for((await _ensure_ws()).recv(), timeout=remaining)
            except asyncio.TimeoutError:
                raise RuntimeError("Daemon did not return call_tool_res in time")
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            # Dynamically extend wait on call_tool_ack for this request
            if msg.get("request_id") == req_id and msg.get("op") == "call_tool_ack":
                ack_timeout = float(msg.get("timeout") or 0) or timeout_s
                grace = float(os.getenv("EXAI_SHIM_ACK_GRACE_SECS", EXAI_SHIM_ACK_GRACE_SECS))
                deadline = asyncio.get_running_loop().time() + ack_timeout + grace
                continue
            # Ignore progress or unrelated messages
            if msg.get("request_id") == req_id and msg.get("op") == "progress":
                continue
            if msg.get("op") == "call_tool_res" and msg.get("request_id") == req_id:
                if msg.get("error"):
                    raise RuntimeError(f"Daemon error: {msg['error']}")
                outs = []
                for o in msg.get("outputs", []):
                    if (o or {}).get("type") == "text":
                        outs.append(TextContent(type="text", text=(o or {}).get("text") or ""))
                    else:
                        outs.append(TextContent(type="text", text=json.dumps(o)))
                return outs
    # Try once, then reconnect and retry once on timeout/connection errors
    try:
        return await _once()
    except Exception as e:
        if "did not return call_tool_res" in str(e) or "ConnectionClosed" in str(type(e)):
            try:
                # Force reconnect
                global _ws
                if _ws and not _ws.closed:
                    await _ws.close()
                _ws = None
                return await _once()
            except Exception:
                raise
        raise

# Single stdio entrypoint (cleaned up)

def main() -> None:
    init_opts = server.create_initialization_options()
    try:
        from mcp.server.stdio import stdio_server as _stdio_server
        async def _runner():
            async with _stdio_server() as (read_stream, write_stream):
                await server.run(read_stream, write_stream, init_opts)
        asyncio.run(_runner())
    except KeyboardInterrupt:
        logger.info("EX WS Shim interrupted; exiting cleanly")
    except Exception:
        logger.exception("EX WS Shim fatal error during stdio_server")
        sys.exit(1)


if __name__ == "__main__":
    main()

