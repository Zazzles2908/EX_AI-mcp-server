"""
Fallback orchestrator helpers for EXAI-WS server.
P0 scope: file_chat flows only.
P1 scope: extend to chat_with_tools; integrate simple circuit breakers.
"""
from __future__ import annotations

import json
import logging
import os
import asyncio as _aio
from typing import Any, Callable, Dict, List

from mcp.types import TextContent

try:
    from src.server.circuit import circuit
except Exception:
    circuit = None  # type: ignore

Logger = logging.getLogger


def _provider_for_tool(tool_name: str) -> str:
    t = (tool_name or "").lower()
    if t.startswith("kimi_"):
        return "KIMI"
    if t.startswith("glm_"):
        return "GLM"
    if t == "chat":
        return "GENERIC"
    return "unknown"


def _is_error_envelope(res: List[TextContent]) -> bool:
    """Detect explicit error envelopes only; avoid false positives on valid outputs.
    - Treat empty responses as non-errors (do not trigger fallback automatically)
    - Only flag explicit error statuses: execution_error, cancelled, failed, timeout, error
    - Recognize success indicators: success, ok, completed
    - Check for actual content presence before flagging
    - Default to non-error for ambiguous cases
    """
    mlog = logging.getLogger("mcp_activity")
    try:
        if not res:
            return False
        txt = getattr(res[0], "text", None)
        if not isinstance(txt, str):
            return False
        s = txt.strip()
        if not s:
            return False
        obj = None
        try:
            obj = json.loads(s)
        except Exception:
            # Plain text (assume success)
            return False
        if isinstance(obj, dict):
            try:
                mlog.info(f"[FALLBACK] received envelope: status={obj.get('status')} error_class={obj.get('error_class')}")
            except Exception:
                pass
            status = str(obj.get("status", "")).lower().strip()
            if status in {"execution_error", "cancelled", "failed", "timeout", "error"}:
                return True
            if status in {"success", "ok", "completed"}:
                content = obj.get("content")
                if content in (None, "", [], {}):
                    try:
                        mlog.warning("[FALLBACK] success status but empty content (not flagging as error)")
                    except Exception:
                        pass
                return False
            if obj.get("error") or obj.get("error_class"):
                return True
            if obj.get("content"):
                return False
        return False
    except Exception:
        return False


async def _attempt_tool(tools: Dict[str, Any], execute_with_monitor: Callable[[Callable[[], Any]], Any], tool_name: str, args: Dict[str, Any]) -> List[TextContent] | None:
    mlog = logging.getLogger("mcp_activity")
    if tool_name not in tools:
        return None
    attempt_timeout = float(os.getenv("FALLBACK_ATTEMPT_TIMEOUT_SECS", "60"))
    provider = _provider_for_tool(tool_name)
    if circuit and provider in {"KIMI", "GLM"} and not circuit.allow(provider, cooloff_seconds=int(os.getenv("CIRCUIT_COOLOFF_SECS", "60"))):
        mlog.warning(f"[CIRCUIT] open for provider={provider}; skipping tool={tool_name}")
        return None
    mlog.info(f"[FALLBACK] attempt tool={tool_name} timeout={attempt_timeout}s provider={provider}")
    tool_obj = tools[tool_name]
    try:
        result = await _aio.wait_for(
            execute_with_monitor(lambda: tool_obj.execute(args)),
            timeout=attempt_timeout,
        )
    except _aio.TimeoutError:
        mlog.error(f"[FALLBACK] timeout on {tool_name} after {attempt_timeout}s")
        if circuit and provider in {"KIMI", "GLM"}:
            circuit.record_failure(provider, failure_threshold=int(os.getenv("CIRCUIT_FAILURES_OPEN", "3")))
        return None
    except Exception as e:
        mlog.error(f"[FALLBACK] exception on {tool_name}: {e}")
        if circuit and provider in {"KIMI", "GLM"}:
            circuit.record_failure(provider, failure_threshold=int(os.getenv("CIRCUIT_FAILURES_OPEN", "3")))
        return None

    if _is_error_envelope(result):
        mlog.warning(f"[FALLBACK] envelope indicates error on tool={tool_name}")
        if circuit and provider in {"KIMI", "GLM"}:
            circuit.record_failure(provider, failure_threshold=int(os.getenv("CIRCUIT_FAILURES_OPEN", "3")))
        return None

    # Success path
    if circuit and provider in {"KIMI", "GLM"}:
        circuit.record_success(provider, success_reset=int(os.getenv("CIRCUIT_SUCCESS_RESET", "2")))
    return result


async def execute_file_chat_with_fallback(
    tools: Dict[str, Any],
    execute_with_monitor: Callable[[Callable[[], Any]], Any],
    primary_name: str,
    args: Dict[str, Any],
) -> List[TextContent]:
    """
    Attempt file-based chat on the primary provider, then gracefully degrade.
    Chain: primary -> glm_multi_file_chat -> chat (final fallback)
    """
    mlog = logging.getLogger("mcp_activity")
    chain = [primary_name, "glm_multi_file_chat"]
    for tool_name in chain:
        # For the primary tool, allow a single quick retry with backoff if the first attempt fails fast
        if tool_name == primary_name:
            res = await _attempt_tool(tools, execute_with_monitor, tool_name, args)
            if res:
                return res
            try:
                backoff = float(os.getenv("FALLBACK_RETRY_BACKOFF_SECS", "1.0"))
                logging.getLogger("mcp_activity").info(f"[FALLBACK] primary retry after backoff={backoff}s tool={tool_name}")
                await _aio.sleep(backoff)
            except Exception:
                pass
            res = await _attempt_tool(tools, execute_with_monitor, tool_name, args)
            if res:
                return res
            # continue to next tool in chain
            continue
        # Non-primary tools: single attempt
        res = await _attempt_tool(tools, execute_with_monitor, tool_name, args)
        if res:
            return res

    # Opportunistic local content injection before plain chat fallback
    try:
        files = args.get("files") or []
        if isinstance(files, list) and files and "chat" in tools:
            from pathlib import Path as _P
            cap = int(os.getenv("FALLBACK_LOCAL_INJECT_MAX_BYTES", os.getenv("KIMI_MF_INJECT_MAX_BYTES", "51200")))
            injected_parts: list[str] = []
            root = os.getenv("EX_PROJECT_ROOT") or os.getcwd()
            total = 0
            for f in files:
                try:
                    p = _P(f)
                    if not p.is_absolute():
                        p = _P(root) / f
                    if not p.exists():
                        # try basename within root
                        p2 = _P(root) / p.name
                        if p2.exists():
                            p = p2
                    if p.exists() and p.is_file():
                        data = p.read_bytes()
                        take = min(cap - total, len(data))
                        if take <= 0:
                            break
                        snippet = data[:take].decode("utf-8", errors="ignore")
                        injected_parts.append(f"[BEGIN FILE {p.name}]\n" + snippet + "\n[END FILE]\n")
                        total += take
                except Exception:
                    continue
            if injected_parts:
                fb_prompt = (args.get("prompt") or "Summarize the provided files succinctly.").strip()
                prompt = (
                    "Files upload unavailable; proceed using these inline excerpts (may be truncated).\n\n" +
                    "\n\n".join(injected_parts) +
                    f"\n\nTask: {fb_prompt}"
                )
                chat_args = {"prompt": prompt, "model": args.get("model")}
                mlog.info("[FALLBACK] invoking 'chat' fallback with local inline excerpts")
                return await execute_with_monitor(lambda: tools["chat"].execute(chat_args))
    except Exception:
        pass

    # Final fallback to plain chat
    try:
        if "chat" in tools:
            fb_prompt = args.get("prompt") or "Please proceed with a concise answer based on your own knowledge."
            chat_args = {"prompt": f"Files-based path unavailable; answer succinctly: {fb_prompt}", "model": args.get("model")}
            mlog.info("[FALLBACK] invoking final 'chat' fallback")
            return await execute_with_monitor(lambda: tools["chat"].execute(chat_args))
    except Exception:
        pass

    return [TextContent(type="text", text=json.dumps({
        "status": "execution_error",
        "error_class": "exhausted_fallback_chain",
        "provider": "unknown",
        "tool": primary_name,
        "detail": "All fallbacks failed; no content available",
    }, ensure_ascii=False))]


def _extract_prompt(args: Dict[str, Any]) -> str:
    p = str(args.get("prompt") or "").strip()
    if p:
        return p
    try:
        msgs = args.get("messages") or []
        if isinstance(msgs, list) and msgs:
            for m in reversed(msgs):
                if isinstance(m, dict) and str(m.get("role", "")).lower() in {"user", "system"}:
                    c = m.get("content")
                    if isinstance(c, str) and c.strip():
                        return c.strip()
    except Exception:
        pass
    return ""


async def execute_chat_with_tools_with_fallback(
    tools: Dict[str, Any],
    execute_with_monitor: Callable[[Callable[[], Any]], Any],
    primary_name: str,
    args: Dict[str, Any],
) -> List[TextContent]:
    """
    Attempt tool-enabled chat on primary provider, then fall back to plain chat.
    Chain: primary -> chat (final fallback)
    """
    mlog = logging.getLogger("mcp_activity")
    chain = [primary_name]
    for tool_name in chain:
        res = await _attempt_tool(tools, execute_with_monitor, tool_name, args)
        if res:
            return res

    # Final fallback to plain chat using prompt derived from messages
    try:
        if "chat" in tools:
            fb_prompt = _extract_prompt(args) or "Provide a concise answer."
            chat_args = {"prompt": fb_prompt, "model": args.get("model")}
            mlog.info("[FALLBACK] invoking 'chat' fallback for chat_with_tools")
            return await execute_with_monitor(lambda: tools["chat"].execute(chat_args))
    except Exception:
        pass

    return [TextContent(type="text", text=json.dumps({
        "status": "execution_error",
        "error_class": "exhausted_fallback_chain",
        "provider": "unknown",
        "tool": primary_name,
        "detail": "All fallbacks failed; no content available",
    }, ensure_ascii=False))]

