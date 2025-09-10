"""
Remote (network) MCP server for EX MCP Server.

This module exposes the existing MCP Server over HTTP(S) using SSE/WebSockets via FastAPI.
It attempts to use available adapters in the following order:

1) Official MCP FastAPI adapter (if present in the installed mcp package)
2) fastmcp (community adapter) if installed
3) Fallback: health/CORS/auth endpoints only with a 501 for /mcp

Environment variables:
- MCP_REMOTE_HOST (default: 0.0.0.0)
- MCP_REMOTE_PORT (default: 7800)
- MCP_BASE_PATH (default: /mcp)
- MCP_AUTH_TOKEN (optional; if set, clients must present Authorization: Bearer <token>)
- CORS_ORIGINS (CSV; default: *)
- LOG_LEVEL (INFO/DEBUG/...) — passed through to uvicorn/root logger

Usage (local):
  uvicorn remote_server:app --host 0.0.0.0 --port 7800

Docker (after building):
  docker run -e MCP_AUTH_TOKEN=secret -p 7800:7800 ex-mcp:latest

Note: To enable full remote MCP over SSE/WebSocket, install extras:
  pip install .[remote]

This includes: fastapi, uvicorn, sse-starlette, and fastmcp (if needed).
"""
from __future__ import annotations

import os
import logging
from typing import Any

from fastapi import FastAPI, Request, WebSocket, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

# Reuse existing MCP Server instance and InitializationOptions from server.py
from mcp.server.models import InitializationOptions
from mcp.types import PromptsCapability, ServerCapabilities, ToolsCapability
from server import server as mcp_server  # existing Server("ex-server")
from config import __version__

logger = logging.getLogger(__name__)

MCP_BASE_PATH = os.getenv("MCP_BASE_PATH", "/mcp").rstrip("/")
AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "").strip()

# Alternative/common MCP paths used by popular servers (comma-separated override supported)
_alt_paths_csv = os.getenv("MCP_ALT_PATHS", "/sse,/v1/sse").strip()
ALT_BASE_PATHS = [p if p.startswith("/") else f"/{p}" for p in [s.strip() for s in _alt_paths_csv.split(",") if s.strip()]]

# CORS setup
cors_csv = os.getenv("CORS_ORIGINS", "*").strip()
if cors_csv == "*":
    cors_origins = ["*"]
else:
    cors_origins = [o.strip() for o in cors_csv.split(",") if o.strip()]

# Create FastAPI app
app = FastAPI(title="EX MCP Remote Server", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Protect these URL prefixes with auth
PROTECTED_PREFIXES = [MCP_BASE_PATH] + [p.rstrip("/") for p in ALT_BASE_PATHS if p.rstrip("/") != MCP_BASE_PATH]


def _auth_dependency(request: Request):
    if not AUTH_TOKEN:
        return  # open access
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    if token != AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "version": __version__}


# Attempt to mount an SSE/WebSocket MCP endpoint
_mounted = False
_init_opts = InitializationOptions(
    server_name=os.getenv("MCP_SERVER_NAME", "EX MCP Server"),
    server_version=__version__,
    capabilities=ServerCapabilities(tools=ToolsCapability(), prompts=PromptsCapability()),
)

# Strategy: fastmcp (explicit) + optional alternate paths
try:
    from importlib import import_module
    fm = import_module("fastmcp")
    app_factory = None
    for attr in ("make_fastapi_app", "create_fastapi_app", "fastapi_app"):
        app_factory = getattr(fm, attr, None) or app_factory
    if not app_factory:
        raise RuntimeError("fastmcp is installed but no FastAPI factory found")

    # Mount at primary base path
    app_factory(app=app, server=mcp_server, base_path=MCP_BASE_PATH, initialization_options=_init_opts)
    _mounted = True
    logger.info(f"Mounted MCP via fastmcp at {MCP_BASE_PATH}")

    # Also mount at common alternate paths
    for alt in ALT_BASE_PATHS:
        if alt.rstrip("/") != MCP_BASE_PATH:
            try:
                app_factory(app=app, server=mcp_server, base_path=alt.rstrip("/"), initialization_options=_init_opts)
                logger.info(f"Mounted MCP via fastmcp at alternate path {alt}")
            except Exception as e:
                logger.debug(f"Failed to mount alternate path {alt}: {e}")
except Exception as e:  # pragma: no cover
    logger.debug(f"fastmcp not available or failed to initialize: {e}")


# Fallback endpoint if no adapter succeeded
if not _mounted:
    @app.get(f"{MCP_BASE_PATH}")
    async def mcp_placeholder(req: Request, _dep: Any = Depends(_auth_dependency)):
        return JSONResponse(
            status_code=501,
            content={
                "error": "MCP remote transport not enabled",
                "hint": "Install remote extras: pip install .[remote] and ensure compatible MCP adapter is installed.",
            },
        )


# Security wrapper for all MCP endpoints (SSE/WebSocket). If adapters mounted routes, we add a simple guard.
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Protect under known MCP URL prefixes
    path = request.url.path.rstrip("/") or "/"
    if any(path.startswith(p) for p in PROTECTED_PREFIXES):
        try:
            _auth_dependency(request)
        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    return await call_next(request)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("MCP_REMOTE_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_REMOTE_PORT", "7800"))
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    uvicorn.run("remote_server:app", host=host, port=port, reload=False, log_level=log_level)

