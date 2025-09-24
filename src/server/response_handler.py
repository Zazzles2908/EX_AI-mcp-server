"""
Response handling helpers for MCP server.
Import-safe, minimal surface. Uses utils.response_envelope for summary lines.
"""
from __future__ import annotations
from typing import Any, Dict, Optional

try:
    from src.utils.response_envelope import mcp_call_summary, response_normalized_len_line
except Exception:  # pragma: no cover - keep import-safe in partial environments
    def mcp_call_summary(**kwargs) -> str:  # type: ignore
        return "MCP_CALL_SUMMARY: unavailable"
    def response_normalized_len_line(**kwargs) -> str:  # type: ignore
        return "RESPONSE_DEBUG: unavailable"


class ResponseHandler:
    """Builds standardized logs/envelopes for tool executions."""

    def build_summary(self,
                      tool: str,
                      status: str,
                      step: str = "1/?",
                      dur: Optional[str] = None,
                      model: Optional[str] = None,
                      tokens: Optional[str] = None,
                      cont_id: Optional[str] = None,
                      expert_enabled: Optional[bool] = None,
                      req_id: Optional[str] = None) -> str:
        return mcp_call_summary(tool=tool, status=status, step=step, dur=dur or "-",
                                model=model, tokens=tokens, cont_id=cont_id,
                                expert_enabled=expert_enabled, req_id=req_id)

    def build_response_debug_len(self, tool: str, raw: Any, req_id: Optional[str] = None) -> str:
        return response_normalized_len_line(tool=tool, raw=raw, req_id=req_id)

