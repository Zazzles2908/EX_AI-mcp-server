from __future__ import annotations
import json
import os
from typing import Any, Dict, List
from mcp.types import TextContent
from .shared.base_tool import BaseTool
from tools.shared.base_models import ToolRequest
from src.providers.kimi import KimiModelProvider
from src.providers.registry import ModelProviderRegistry
from src.providers.base import ProviderType

class KimiChatWithToolsTool(BaseTool):
    def get_name(self) -> str:
        return "kimi_chat_with_tools"

    def get_description(self) -> str:
        return (
            "Call Kimi chat completion with optional tools/tool_choice. Can auto-inject an internet tool based on env.\n"
            "Examples:\n"
            "- {\"messages\":[\"Summarize README.md\"], \"model\":\"auto\"}\n"
            "- {\"messages\":[\"research X\"], \"use_websearch\":true, \"tool_choice\":\"auto\"}"
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "messages": {"type": "array"},
                "model": {"type": "string", "default": os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview")},
                "tools": {"type": "array"},
                "tool_choice": {"type": "string"},
                "temperature": {"type": "number", "default": 0.6},
                "stream": {"type": "boolean", "default": False},
                # Fixed: use_websearch (without $ prefix)
                "use_websearch": {"type": "boolean", "default": False},
            },
            "required": ["messages"],
        }

    def get_system_prompt(self) -> str:
        return (
            "You are a Kimi chat orchestrator with tool-use support.\n"
            "Purpose: Call Kimi chat completions with optional tools and tool_choice.\n\n"
            "Parameters:\n"
            "- messages: OpenAI-compatible message array.\n"
            "- model: Kimi model id (default via KIMI_DEFAULT_MODEL).\n"
            "- tools: Optional OpenAI tools spec array; may be auto-injected from env.\n"
            "- tool_choice: 'auto'|'none'|'required' or provider-specific structure.\n"
            "- temperature, stream.\n\n"
            "Provider Features:\n"
            "- use_websearch: When True, injects Kimi's built-in $web_search tool for internet search.\n"
            "- File context can be added separately via kimi_upload_and_extract/kimi_multi_file_chat.\n\n"
            "Output: Return the raw response JSON (choices, usage). Keep responses concise and on-task."
        )

    def get_request_model(self):
        return ToolRequest

    def requires_model(self) -> bool:
        return False

    async def prepare_prompt(self, request: ToolRequest) -> str:
        return ""

    def format_response(self, response: str, request: ToolRequest, model_info: dict | None = None) -> str:
        return response

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        # Resolve provider instance from registry; force Kimi provider and model id
        requested_model = arguments.get("model") or os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview")
        # Map any non-Kimi requests (e.g., 'auto', 'glm-4.5-flash') to a valid Kimi default
        if requested_model not in {"kimi-k2-0711-preview","kimi-k2-0905-preview","kimi-k2-turbo-preview","kimi-latest","kimi-thinking-preview","moonshot-v1-8k","moonshot-v1-32k","moonshot-v1-128k","moonshot-v1-8k-vision-preview","moonshot-v1-32k-vision-preview","moonshot-v1-128k-vision-preview"}:
            requested_model = os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview")

        prov = ModelProviderRegistry.get_provider(ProviderType.KIMI)
        if not isinstance(prov, KimiModelProvider):
            api_key = os.getenv("KIMI_API_KEY", "")
            if not api_key:
                raise RuntimeError("KIMI_API_KEY is not configured")
            prov = KimiModelProvider(api_key=api_key)

        # Observability: log final provider/model and flags (debug-level, no secrets)
        try:
            import logging
            logging.getLogger("kimi_tools_chat").info(
                "KimiChatWithTools: provider=KIMI model=%s stream=%s use_web=%s tools=%s tool_choice=%s",
                requested_model,
                stream_flag if 'stream_flag' in locals() else None,
                bool(arguments.get("use_websearch", False)),
                bool(tools),
                tool_choice,
            )
        except Exception:
            pass

        # Normalize tools and tool_choice
        tools = arguments.get("tools")
        tool_choice = arguments.get("tool_choice")
        # Accept JSON strings for tools and normalize to list/dict per OpenAI schema
        if isinstance(tools, str):
            try:
                tools = json.loads(tools)
            except Exception:
                tools = None  # let provider run without tools rather than 400
        # Normalize tools into list[dict] per provider schema
        if isinstance(tools, list):
            coerced: list[dict] = []
            for it in tools:
                if isinstance(it, dict):
                    coerced.append(it)
                elif isinstance(it, str):
                    nm = it.strip()
                    if nm.startswith("$"):
                        # Builtin function shorthand like "$web_search"
                        coerced.append({"type": "builtin_function", "function": {"name": nm}})
                    else:
                        # Drop unrecognized string tool spec to avoid provider 400s
                        continue
                else:
                    # Unsupported type - drop
                    continue
            tools = coerced or None
        elif tools is not None and not isinstance(tools, list):
            tools = [tools] if isinstance(tools, dict) else None

        # Standardize tool_choice to allowed strings when a complex object isn't provided
        if isinstance(tool_choice, str):
            lc = tool_choice.strip().lower()
            if lc in {"auto", "none", "required"}:
                tool_choice = lc
            else:
                tool_choice = None

        # Websearch tool injection via provider capabilities layer for consistency
        use_websearch = bool(arguments.get("use_websearch", False)) or (
            os.getenv("KIMI_ENABLE_INTERNET_TOOL", "false").strip().lower() == "true" or
            os.getenv("KIMI_ENABLE_INTERNET_SEARCH", "false").strip().lower() == "true"
        )
        if use_websearch and bool(arguments.get("use_websearch", False)):
            try:
                from src.providers.capabilities import get_capabilities_for_provider
                caps = get_capabilities_for_provider(ProviderType.KIMI)
                ws = caps.get_websearch_tool_schema({"use_websearch": True})
                if ws.tools:
                    tools = (tools or []) + ws.tools
                if tool_choice is None and ws.tool_choice is not None:
                    tool_choice = ws.tool_choice
            except Exception:
                # If capabilities lookup fails, proceed without injecting tools
                pass

        # Normalize messages into OpenAI-style list of {role, content}
        raw_msgs = arguments.get("messages")
        norm_msgs: list[dict[str, Any]] = []
        if isinstance(raw_msgs, str):
            norm_msgs = [{"role": "user", "content": raw_msgs}]
        elif isinstance(raw_msgs, list):
            for item in raw_msgs:
                if isinstance(item, str):
                    norm_msgs.append({"role": "user", "content": item})
                elif isinstance(item, dict):
                    role = item.get("role") or "user"
                    content = item.get("content")
                    # sometimes clients pass {"text": ...}
                    if content is None and "text" in item:
                        content = item.get("text")
                    # fallback to string cast to avoid 400s
                    if content is None:
                        content = ""
                    norm_msgs.append({"role": str(role), "content": str(content)})
                else:
                    # best-effort coercion
                    norm_msgs.append({"role": "user", "content": str(item)})
        else:
            # final fallback to prevent provider 400s
            norm_msgs = [{"role": "user", "content": str(raw_msgs)}]

        import asyncio as _aio
        stream_flag = bool(arguments.get("stream", os.getenv("KIMI_CHAT_STREAM_DEFAULT", "false").strip().lower() == "true"))
        model_used = requested_model

        if stream_flag:
            # For web-enabled flows, prefer the non-stream tool-call loop for reliability (handles tool_calls)
            if bool(arguments.get("use_websearch", False)):
                stream_flag = False
            else:
                # Handle streaming in a background thread; accumulate content (no tool_calls loop in stream mode)
                def _stream_call():
                    content_parts = []
                    raw_items = []
                    try:
                        # Streaming: fall back to direct client but include extra headers for idempotency/cache when possible
                        extra_headers = {}
                        try:
                            ck = arguments.get("_call_key") or arguments.get("call_key")
                            if ck:
                                extra_headers["Idempotency-Key"] = str(ck)
                            ctok = getattr(prov, "get_cache_token", None)
                            sid = arguments.get("_session_id")
                            if ctok and sid:
                                # Best-effort prefix hash similar to provider wrapper
                                import hashlib
                                parts = []
                                for m in norm_msgs[:6]:
                                    parts.append(str(m.get("role","")) + "\n" + str(m.get("content",""))[:2048])
                                pf = hashlib.sha256("\n".join(parts).encode("utf-8", errors="ignore")).hexdigest()
                                t = prov.get_cache_token(sid, "kimi_chat_with_tools", pf)
                                if t:
                                    extra_headers["Msh-Context-Cache-Token"] = t
                        except Exception:
                            pass
                        for evt in prov.client.chat.completions.create(
                            model=model_used,
                            messages=norm_msgs,
                            tools=tools,
                            tool_choice=tool_choice,
                            temperature=float(arguments.get("temperature", 0.6)),
                            stream=True,
                            extra_headers=extra_headers or None,
                        ):
                            raw_items.append(evt)
                            try:
                                ch = getattr(evt, "choices", None) or []
                                if ch:
                                    delta = getattr(ch[0], "delta", None)
                                    if delta:
                                        piece = getattr(delta, "content", None)
                                        if piece:
                                            content_parts.append(str(piece))
                            except Exception:
                                pass
                    except Exception as e:
                        raise e
                    return ("".join(content_parts), raw_items)

                content_text, raw_stream = await _aio.to_thread(_stream_call)
                normalized = {
                    "provider": "KIMI",
                    "model": model_used,
                    "content": content_text,
                    "tool_calls": None,
                    "usage": None,
                    "raw": {"stream": True, "items": [str(it) for it in raw_stream[:10]]},
                }
                return [TextContent(type="text", text=json.dumps(normalized, ensure_ascii=False))]
        else:
            # Non-streaming with minimal tool-call loop for function web_search
            import copy
            import urllib.parse, urllib.request

            def _extract_tool_calls(raw_any: any) -> list[dict] | None:
                try:
                    payload = raw_any
                    if hasattr(payload, "model_dump"):
                        payload = payload.model_dump()
                    choices = payload.get("choices") or []
                    if not choices:
                        return None
                    msg = choices[0].get("message") or {}
                    tcs = msg.get("tool_calls")
                    return tcs if tcs else None
                except Exception:
                    return None

            def _run_web_search_backend(query: str) -> dict:
                # Pluggable backend controlled by env SEARCH_BACKEND: duckduckgo | tavily | bing
                backend = os.getenv("SEARCH_BACKEND", "duckduckgo").strip().lower()
                try:
                    if backend == "tavily":
                        api_key = os.getenv("TAVILY_API_KEY", "").strip()
                        if not api_key:
                            raise RuntimeError("TAVILY_API_KEY not set")
                        payload = json.dumps({"api_key": api_key, "query": query, "max_results": 5}).encode("utf-8")
                        req = urllib.request.Request("https://api.tavily.com/search", data=payload, headers={"Content-Type": "application/json"})
                        with urllib.request.urlopen(req, timeout=25) as resp:
                            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                            results = []
                            for it in (data.get("results") or [])[:5]:
                                url = it.get("url") or it.get("link")
                                if url:
                                    results.append({"title": it.get("title") or it.get("snippet"), "url": url})
                            return {"engine": "tavily", "query": query, "results": results}
                    if backend == "bing":
                        key = os.getenv("BING_SEARCH_API_KEY", "").strip()
                        if not key:
                            raise RuntimeError("BING_SEARCH_API_KEY not set")
                        q = urllib.parse.urlencode({"q": query})
                        req = urllib.request.Request(f"https://api.bing.microsoft.com/v7.0/search?{q}")
                        req.add_header("Ocp-Apim-Subscription-Key", key)
                        with urllib.request.urlopen(req, timeout=25) as resp:
                            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                            results = []
                            for it in (data.get("webPages", {}).get("value", [])[:5]):
                                if it.get("url"):
                                    results.append({"title": it.get("name"), "url": it.get("url")})
                            return {"engine": "bing", "query": query, "results": results}
                    # Default: DuckDuckGo Instant Answer API
                    q = urllib.parse.urlencode({"q": query, "format": "json", "no_html": 1, "skip_disambig": 1})
                    url = f"https://api.duckduckgo.com/?{q}"
                    with urllib.request.urlopen(url, timeout=20) as resp:
                        data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                        results = []
                        if data.get("AbstractURL"):
                            results.append({"title": data.get("Heading"), "url": data.get("AbstractURL")})
                        for item in (data.get("RelatedTopics") or [])[:5]:
                            if isinstance(item, dict) and item.get("FirstURL"):
                                results.append({"title": item.get("Text"), "url": item.get("FirstURL")})
                        return {"engine": "duckduckgo", "query": query, "results": results[:5]}
                except Exception as e:
                    return {"engine": backend or "duckduckgo", "query": query, "error": str(e), "results": []}

            messages_local = copy.deepcopy(norm_msgs)

            for _ in range(3):  # limit tool loop depth
                def _call():
                    return prov.chat_completions_create(
                        model=model_used,
                        messages=messages_local,
                        tools=tools,
                        tool_choice=tool_choice,
                        temperature=float(arguments.get("temperature", 0.6)),
                        _session_id=arguments.get("_session_id"),
                        _call_key=arguments.get("_call_key"),
                        _tool_name=self.get_name(),
                    )
                # Apply per-call timeout to avoid long hangs on web-enabled prompts
                # Choose timeout based on whether web search is enabled
                try:
                    if bool(arguments.get("use_websearch", False)):
                        timeout_secs = float(os.getenv("KIMI_CHAT_TOOL_TIMEOUT_WEB_SECS", "300"))
                    else:
                        timeout_secs = float(os.getenv("KIMI_CHAT_TOOL_TIMEOUT_SECS", "180"))
                except Exception:
                    timeout_secs = 180.0
                try:
                    result = await _aio.wait_for(_aio.to_thread(_call), timeout=timeout_secs)
                except _aio.TimeoutError:
                    err = {"status": "execution_error", "error": f"Kimi chat timed out after {int(timeout_secs)}s"}
                    return [TextContent(type="text", text=json.dumps(err, ensure_ascii=False))]

                # If no tool calls, return immediately
                tcs = _extract_tool_calls(result.get("raw")) if isinstance(result, dict) else None
                if not tcs:
                    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

                # Execute supported tools locally (function web_search)
                tool_msgs = []
                for tc in tcs:
                    try:
                        fn = tc.get("function") or {}
                        fname = (fn.get("name") or "").strip()
                        fargs_raw = fn.get("arguments")
                        fargs = {}
                        if isinstance(fargs_raw, str):
                            try:
                                fargs = json.loads(fargs_raw)
                            except Exception:
                                fargs = {"query": fargs_raw}
                        elif isinstance(fargs_raw, dict):
                            fargs = fargs_raw

                        if fname in ("web_search",):
                            query = fargs.get("query") or ""
                            res = _run_web_search_backend(query)
                            tool_msgs.append({
                                "role": "tool",
                                "tool_call_id": str(tc.get("id") or tc.get("tool_call_id") or (tc.get("function",{}).get("id") if isinstance(tc.get("function"), dict) else "")) or "tc-0",
                                "content": json.dumps(res, ensure_ascii=False),
                            })
                        else:
                            # Unsupported tool - return partial with hint
                            return [TextContent(type="text", text=json.dumps({
                                "status": "tool_call_pending",
                                "note": f"Unsupported tool {fname}. Supported: web_search.",
                                "raw": result.get("raw"),
                            }, ensure_ascii=False))]
                    except Exception as e:
                        return [TextContent(type="text", text=json.dumps({
                            "status": "tool_call_error",
                            "error": str(e),
                            "raw": result.get("raw"),
                        }, ensure_ascii=False))]

                # Append tool messages and continue the loop
                messages_local.extend(tool_msgs)

            # If we exit loop due to depth, return last result
            return [TextContent(type="text", text=json.dumps({
                "status": "max_tool_depth_reached",
                "raw": result if isinstance(result, dict) else {},
            }, ensure_ascii=False))]
