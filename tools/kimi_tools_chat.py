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

        # Fixed: Check for use_websearch (without $ prefix)
        use_websearch = bool(arguments.get("use_websearch", False)) or (
            os.getenv("KIMI_ENABLE_INTERNET_TOOL", "false").strip().lower() == "true" or
            os.getenv("KIMI_ENABLE_INTERNET_SEARCH", "false").strip().lower() == "true"
        )

        # Safety: do not inject web_search unless explicitly requested in arguments
        # This prevents unexpected tool_calls when the caller didn't ask for web.
        if use_websearch and bool(arguments.get("use_websearch", False)):
            web_search_tool = {"type": "builtin_function", "function": {"name": "$web_search"}}
            tools = (tools or []) + [web_search_tool]
            if tool_choice is None:
                tool_choice = os.getenv("KIMI_DEFAULT_TOOL_CHOICE", "auto")

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
            # Handle streaming in a background thread; accumulate content
            def _stream_call():
                content_parts = []
                raw_items = []
                try:
                    for evt in prov.client.chat.completions.create(
                        model=model_used,
                        messages=norm_msgs,
                        tools=tools,
                        tool_choice=tool_choice,
                        temperature=float(arguments.get("temperature", 0.6)),
                        stream=True,
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
            # Non-streaming: offload blocking call to background thread
            completion = await _aio.to_thread(
                prov.client.chat.completions.create,
                model=model_used,
                messages=norm_msgs,
                tools=tools,
                tool_choice=tool_choice,
                temperature=float(arguments.get("temperature", 0.6)),
                stream=False,
            )

            from pydantic.json import pydantic_encoder
            try:
                raw_text = json.dumps(completion, default=pydantic_encoder, ensure_ascii=False)
                raw_obj = json.loads(raw_text)
            except Exception:
                raw_text = str(completion)
                raw_obj = {"_text": raw_text}

            if os.getenv("KIMI_CHAT_RETURN_RAW_ONLY", "false").strip().lower() == "true":
                return [TextContent(type="text", text=raw_text)]

            first_choice = None
            try:
                choices = raw_obj.get("choices") or []
                if choices:
                    first_choice = choices[0]
            except Exception:
                first_choice = None

            content = None
            tool_calls = None
            if isinstance(first_choice, dict):
                msg = first_choice.get("message") or {}
                content = msg.get("content")
                tool_calls = msg.get("tool_calls")

            usage = raw_obj.get("usage")
            normalized = {
                "provider": "KIMI",
                "model": model_used,
                "content": content,
                "tool_calls": tool_calls,
                "usage": usage,
                "raw": raw_obj,
            }
            return [TextContent(type="text", text=json.dumps(normalized, ensure_ascii=False))]