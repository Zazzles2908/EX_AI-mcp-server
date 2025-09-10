from __future__ import annotations
import json
import os
from typing import Any, Dict, List
from mcp.types import TextContent
from .shared.base_tool import BaseTool
from tools.shared.base_models import ToolRequest
from src.providers.kimi import KimiModelProvider
from src.providers.registry import ModelProviderRegistry

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
        # Resolve provider instance from registry; fallback to direct client if not configured
        prov = ModelProviderRegistry.get_provider_for_model(arguments.get("model") or os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview"))
        if not isinstance(prov, KimiModelProvider):
            api_key = os.getenv("KIMI_API_KEY", "")
            if not api_key:
                raise RuntimeError("KIMI_API_KEY is not configured")
            prov = KimiModelProvider(api_key=api_key)

        # Normalize tools and tool_choice
        tools = arguments.get("tools")
        tool_choice = arguments.get("tool_choice")
        # Accept JSON strings for tools and normalize to list/dict per OpenAI schema
        if isinstance(tools, str):
            try:
                tools = json.loads(tools)
            except Exception:
                tools = None  # let provider run without tools rather than 400
        # Ensure tools is a list of dicts
        if tools is not None and not isinstance(tools, list):
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
        
        if use_websearch:
            # Fixed: Use the correct builtin_function format for web search
            web_search_tool = {
                "type": "builtin_function",
                "function": {
                    "name": "$web_search"
                }
            }
            
            if not tools:
                tools = []
            tools.append(web_search_tool)
            
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
        
        completion = prov.client.chat.completions.create(
            model=arguments.get("model") or os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview"),
            messages=norm_msgs,
            tools=tools,
            tool_choice=tool_choice,
            temperature=float(arguments.get("temperature", 0.6)),
            stream=bool(arguments.get("stream", False)),
        )
        
        # Return structured+raw by default; allow raw-only via env flag
        from pydantic.json import pydantic_encoder
        
        # Serialize provider response to a dict
        try:
            raw_text = json.dumps(completion, default=pydantic_encoder, ensure_ascii=False)
            raw_obj = json.loads(raw_text)
        except Exception:
            raw_text = str(completion)
            raw_obj = {"_text": raw_text}
        
        if os.getenv("KIMI_CHAT_RETURN_RAW_ONLY", "false").strip().lower() == "true":
            return [TextContent(type="text", text=raw_text)]
        
        # Normalize primary fields for convenience
        model_used = arguments.get("model") or os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview")
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
            "model": model_used,
            "content": content,
            "tool_calls": tool_calls,
            "usage": usage,
            "raw": raw_obj,
        }
        
        return [TextContent(type="text", text=json.dumps(normalized, ensure_ascii=False))]