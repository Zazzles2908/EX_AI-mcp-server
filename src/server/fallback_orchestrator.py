"""
Fallback orchestrator helpers for EXAI-WS server.
P0 scope: file_chat flows only.
"""
from __future__ import annotations

import json
import logging
import os
import asyncio as _aio
from typing import Any, Callable, Dict, List

from mcp.types import TextContent

Logger = logging.getLogger


async def execute_file_chat_with_fallback(
    tools: Dict[str, Any],
    execute_with_monitor: Callable[[Callable[[], Any]], Any],
    primary_name: str,
    args: Dict[str, Any],
) -> List[TextContent]:
    """
    Attempt file-based chat on the primary provider, then gracefully degrade.
    Chain: primary -> glm_multi_file_chat -> chat (final fallback)

    tools: mapping of tool_name -> tool_instance (from server registry)
    execute_with_monitor: server's monitored executor for async callables
    primary_name: entry tool (e.g., "kimi_multi_file_chat")
    args: original arguments
    """
    mlog = logging.getLogger("mcp_activity")

    def _is_error_envelope(res: List[TextContent]) -> bool:
        """Heuristically detect provider failure envelopes embedded in text content."""
        try:
            if not res:
                return True  # treat empty as failure to allow fallback
            txt = getattr(res[0], "text", None)
            if not isinstance(txt, str) or not txt.strip():
                return True
            try:
                obj = json.loads(txt)
            except Exception:
                # Non-JSON text that contains common failure markers
                low = txt.lower()
                return any(k in low for k in ("execution_error", "cancelled", "timeout", "error"))
            if isinstance(obj, dict):
                # NEW: explicit envelope visibility for diagnostics
                try:
                    mlog.info(f"[FALLBACK] received envelope: status={obj.get('status')} error_class={obj.get('error_class')}")
                except Exception:
                    pass

                status = str(obj.get("status", "")).lower()
                if status.startswith("execution_error") or status in {"cancelled", "error", "failed"}:
                    return True
                # Common envelope shapes: {error: {...}}
                if obj.get("error"):
                    return True
        except Exception:
            return True
        return False

    chain = [primary_name, "glm_multi_file_chat"]
    for attempt_idx, tool_name in enumerate(chain, start=1):
        try:
            if tool_name not in tools:
                continue
            attempt_timeout = float(os.getenv("FALLBACK_ATTEMPT_TIMEOUT_SECS", "60"))
            mlog.info(f"[FALLBACK] attempt={attempt_idx} tool={tool_name} timeout={attempt_timeout}s")
            tool_obj = tools[tool_name]
            try:
                # Execute via server monitor to inherit logging/telemetry and uniform cancellation
                result = await _aio.wait_for(
                    execute_with_monitor(lambda: tool_obj.execute(args)),
                    timeout=attempt_timeout,
                )
            except _aio.TimeoutError:
                mlog.error(f"[FALLBACK] timeout on {tool_name} after {attempt_timeout}s; advancing chain")
                continue
            if _is_error_envelope(result):
                mlog.warning(
                    f"[FALLBACK] envelope indicates error; advancing chain from {tool_name}"
                )
                try:
                    mlog.info(f"[FALLBACK] advancing chain due to envelope (tool={tool_name})")
                except Exception:
                    pass
                continue
            return result
        except Exception as e:
            try:
                mlog.error(f"[FALLBACK] exception on {tool_name}: {e}")
            except Exception:
                pass
            continue

    # Final fallback to plain chat to avoid a user-visible failure
    try:
        if "chat" in tools:
            fb_prompt = args.get("prompt") or "Please proceed with a concise answer based on your own knowledge."
            chat_args = {
                "prompt": f"Files-based path unavailable; answer succinctly: {fb_prompt}",
                "model": args.get("model"),
            }
            mlog.info("[FALLBACK] invoking final 'chat' fallback")
            return await execute_with_monitor(lambda: tools["chat"].execute(chat_args))
    except Exception:
        pass

    # Minimal error envelope as last resort
    return [
        TextContent(
            type="text",
            text=json.dumps(
                {
                    "status": "execution_error",
                    "error_class": "exhausted_fallback_chain",
                    "provider": "unknown",
                    "tool": primary_name,
                    "detail": "All fallbacks failed; no content available",
                },
                ensure_ascii=False,
            ),
        )
    ]

