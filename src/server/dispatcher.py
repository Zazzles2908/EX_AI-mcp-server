"""Dispatcher scaffolding for EX MCP Server.

Purpose: provide a thin, testable facade for routing tool calls and model resolution
away from server.py. First pass is non-breaking and NOT YET WIRED.

Next steps (planned):
- Extract handle_call_tool logic to Dispatcher with explicit extension points
- Accept orchestrator and circuit modules via DI to simplify unit testing
"""
from __future__ import annotations
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

class Dispatcher:
    """Placeholder dispatcher (not yet wired)."""
    def __init__(self) -> None:
        self._ready: bool = True

    def is_ready(self) -> bool:
        return self._ready

    def route(self, tool_name: str, arguments: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Non-operative route with telemetry/logging only; returns None."""
        try:
            # Minimal diagnostics to prove call-path without changing behavior
            model_hint = (arguments or {}).get("model", "auto")
            logger.debug(
                "[DISPATCHER.route] noop call tool=%s model_hint=%s arg_count=%s",
                tool_name,
                model_hint,
                len(arguments or {}),
            )
        except Exception as log_err:  # pragma: no cover
            try:
                logger.debug(f"[DISPATCHER.route] logging failed: {log_err}")
            except Exception:
                pass
        return None

