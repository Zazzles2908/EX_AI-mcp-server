"""
Tool wrapper factory and wrapper class for MCP server.
Adds telemetry, logging, and error handling without behavior change.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List

from mcp.types import TextContent

# Import-safe helpers
try:
    from src.server.response_handler import ResponseHandler
    response_handler = ResponseHandler()
except Exception:
    response_handler = None  # type: ignore

try:
    from src.server.conversation_manager import conversation_manager
except Exception:
    # Fallback if conversation_manager not available
    conversation_manager = None  # type: ignore

try:
    from src.server.telemetry import telemetry
    if not hasattr(telemetry, "count") or not hasattr(telemetry, "histogram"):
        telemetry = None  # type: ignore
except Exception:
    telemetry = None  # type: ignore


logger = logging.getLogger(__name__)


class ToolWrapper:
    """Wraps a tool to add telemetry, timing, and error handling."""

    def __init__(self, tool: Any) -> None:
        self._tool = tool
        self.name = getattr(tool, "name", "unknown")
        self.description = getattr(tool, "description", "")
        self._input_schema: Callable[[], Dict[str, Any]] | None = getattr(tool, "get_input_schema", None)

    def get_input_schema(self) -> Dict[str, Any]:
        """Return input schema if available, else empty dict."""
        if self._input_schema:
            try:
                return self._input_schema()
            except Exception:
                pass
        return {}

    async def execute(self, args: Dict[str, Any]) -> List[TextContent]:
        """Execute wrapped tool with telemetry and error handling."""
        req_id = conversation_manager.get_cont_id() if conversation_manager else "no-req-id"
        start = time.perf_counter()
        logger.debug("[ToolWrapper] start tool=%s req_id=%s", self.name, req_id)
        try:
            # Call underlying tool
            result = await self._tool.execute(args)
            # Normalize response
            if isinstance(result, list) and all(isinstance(x, TextContent) for x in result):
                normalized = result
            elif response_handler and hasattr(response_handler, "normalise_to_text_content_list"):
                normalized = response_handler.normalise_to_text_content_list(result)
            else:
                # Fallback: wrap in TextContent
                normalized = [TextContent(type="text", text=str(result))]
            dur_ms = int((time.perf_counter() - start) * 1000)
            logger.debug("[ToolWrapper] success tool=%s req_id=%s dur=%sms", self.name, req_id, dur_ms)
            # Telemetry best-effort
            if telemetry:
                try:
                    telemetry.count(self.name, "success", "wrapped")
                    telemetry.histogram(dur_ms)
                except Exception:
                    pass
            return normalized
        except Exception as exc:
            dur_ms = int((time.perf_counter() - start) * 1000)
            logger.exception("[ToolWrapper] error tool=%s req_id=%s dur=%sms", self.name, req_id, dur_ms)
            # Telemetry best-effort
            if telemetry:
                try:
                    telemetry.count(self.name, "error", "wrapped")
                    telemetry.histogram(dur_ms)
                except Exception:
                    pass
            # Return error envelope
            import json
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "execution_error",
                    "error_class": type(exc).__name__,
                    "error": str(exc),
                    "tool": self.name,
                    "req_id": req_id
                }, ensure_ascii=False)
            )]


def build_wrapped_tools(tools: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap all tools in ToolWrapper and return new dict."""
    wrapped: Dict[str, Any] = {}
    for name, tool in tools.items():
        wrapped[name] = ToolWrapper(tool)
    logger.info("[ToolWrapper] wrapped %s tools", len(wrapped))
    return wrapped

