
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
                _pi = None if PING_INTERVAL <= 