"""
Progress notification helper for EX MCP Server.

- Centralizes progress emission for tools
- Controlled via STREAM_PROGRESS env var (default: true)
- Logs to the "mcp_activity" logger
- Best-effort MCP notification hook (can be wired by server if supported)
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Callable, Optional
from contextvars import ContextVar

# Type for a notifier function; may be sync or async
Notifier = Callable[[str, str], Any]

_logger = logging.getLogger("mcp_activity")
_mcp_notifier: Optional[Notifier] = None

# Per-call progress capture via ContextVar (safe for async concurrency)
_progress_log_var: ContextVar[Optional[list[str]]] = ContextVar("progress_log", default=None)


def _stream_enabled() -> bool:
    return os.getenv("STREAM_PROGRESS", "true").strip().lower() == "true"


def start_progress_capture() -> None:
    """Begin capturing progress messages for the current call."""
    _progress_log_var.set([])


def get_progress_log() -> list[str]:
    """Return captured progress messages for the current call (if any)."""
    buf = _progress_log_var.get()
    return list(buf) if isinstance(buf, list) else []


def set_mcp_notifier(notifier: Notifier) -> None:
    """
    Register a notifier callback capable of sending MCP-compatible notifications.
    The callback should accept (message: str, level: str) and may be sync or async.
    """
    global _mcp_notifier
    _mcp_notifier = notifier


def clear_mcp_notifier() -> None:
    """Clear any registered MCP notifier."""
    global _mcp_notifier
    _mcp_notifier = None


def send_progress(message: str, level: str = "info") -> None:
    """
    Emit a progress signal if STREAM_PROGRESS is enabled.
    - Logs via mcp_activity (picked up by stderr/file handlers)
    - Captures message into per-call buffer (ContextVar)
    - Best-effort call to a registered MCP notifier (if any)
    """
    if not _stream_enabled():
        return

    # Log first so users always see breadcrumbs in stderr/logs
    level_lower = (level or "info").lower()
    if level_lower == "debug":
        _logger.debug(f"[PROGRESS] {message}")
    elif level_lower in ("warn", "warning"):
        _logger.warning(f"[PROGRESS] {message}")
    elif level_lower == "error":
        _logger.error(f"[PROGRESS] {message}")
    else:
        _logger.info(f"[PROGRESS] {message}")

    # Capture in per-call buffer
    try:
        buf = _progress_log_var.get()
        if isinstance(buf, list):
            buf.append(message)
    except Exception:
        pass

    # Best-effort MCP notification
    try:
        if _mcp_notifier is None:
            return
        result = _mcp_notifier(message, level_lower)
        if asyncio.iscoroutine(result):
            # Fire and forget; do not await within tool critical paths
            asyncio.create_task(result)  # type: ignore[arg-type]
    except Exception:
        # Never allow progress emission to break tool execution
        _logger.debug("[PROGRESS] MCP notifier unavailable or failed; continuing")

