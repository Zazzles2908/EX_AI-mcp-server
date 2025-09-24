"""
Lightweight helpers to standardize MCP call summaries and response debug logging.
Non-invasive: used by server to format summary lines consistently.
"""
from __future__ import annotations

from typing import Optional


def mcp_call_summary(
    *,
    tool: str,
    status: str,
    step_no: int | str,
    total_steps: Optional[int] | str,
    duration_sec: float,
    model: str,
    tokens: int | str,
    continuation_id: Optional[str],
    expert_enabled: str | bool,
    req_id: str,
) -> str:
    """Build a single-line MCP_CALL_SUMMARY string.

    Args mirror existing server locals to avoid behavior changes.
    """
    # Normalize fields to match historical formatting
    _total = total_steps if (total_steps is not None and total_steps != "") else "?"
    _cont = continuation_id if (continuation_id and str(continuation_id).strip()) else "-"
    if isinstance(expert_enabled, bool):
        _expert = "Enabled" if expert_enabled else "Disabled"
    else:
        _expert = expert_enabled if expert_enabled else "Disabled"
    return (
        f"MCP_CALL_SUMMARY: tool={tool} status={status} step={step_no}/{_total} "
        f"dur={duration_sec:.1f}s model={model} tokens~={tokens} cont_id={_cont} "
        f"expert={_expert} req_id={req_id}"
    )


def response_normalized_len_line(*, tool: str, req_id: str, length: int) -> str:
    """Return the standard normalized length debug line.

    Kept as a helper to reduce duplication where needed.
    """
    return f"RESPONSE_DEBUG: normalized_result_len={length} tool={tool} req_id={req_id}"

