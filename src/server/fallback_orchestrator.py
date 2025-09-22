"""
Fallback orchestrator helpers for EXAI-WS server.
P0 scope: file_chat flows only.
"""
from __future__ import annotations

import json
import logging
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
        try:
            if not res:
                return False
            txt = getattr(res[0], "text", None)
            if not isinstance(txt, str):
                return False
            obj = json.loads(txt)
            if isinstance(obj, dict) and str(obj.get("status")).startswith("execution_error"):
                return True
        except Exception:
            return False
        return False

    chain = [primary_name, "glm_multi_file_chat"]
    for attempt_idx, tool_name in enumerate(chain, start=1):
        try:
            if tool_name not in tools:
                continue
            mlog.info(f"[FALLBACK] attempt={attempt_idx} tool={tool_name}")
            tool_obj = tools[tool_name]
            result = await execute_with_monitor(lambda: tool_obj.execute(args))
            if _is_error_envelope(result):
                mlog.warning(
                    f"[FALLBACK] envelope indicates error; advancing chain from {tool_name}"
                )
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

