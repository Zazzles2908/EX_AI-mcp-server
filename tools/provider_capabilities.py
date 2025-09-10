from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from mcp.types import TextContent

from .shared.base_tool import BaseTool
from tools.shared.base_models import ToolRequest


class ProviderCapabilitiesTool(BaseTool):
    def get_name(self) -> str:
        return "provider_capabilities"

    def get_description(self) -> str:
        return "Summarize provider configuration and capabilities (keys presence only, active tools, key endpoints). Safe, no secrets."

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "include_tools": {"type": "boolean", "default": True},
                "show_advanced": {"type": "boolean", "default": False},
                "invalidate_cache": {"type": "boolean", "default": False},
            },
        }

    def get_system_prompt(self) -> str:
        return (
            "You summarize provider readiness safely.\n"
            "Purpose: Report presence of keys (names only), key endpoints, and active tools without revealing secrets.\n\n"
            "Behavior:\n- Read env for known settings (KIMI/GLM URLs, flags).\n- Optionally list loaded tools via ToolRegistry.\n\n"
            "Output: Compact JSON {env: {...}, tools: [...]}."
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
        include_tools = bool(arguments.get("include_tools", True))
        show_advanced = bool(arguments.get("show_advanced", False))
        invalidate_cache = bool(arguments.get("invalidate_cache", False))

        # Tiny TTL cache (module-level)
        try:
            from time import time
            cache_key = f"pcap:{int(time()//90)}"  # 90-second buckets
            global _PCAP_CACHE
            if invalidate_cache:
                _PCAP_CACHE = None
            if '_PCAP_CACHE' not in globals():
                _PCAP_CACHE = {}
        except Exception:
            _PCAP_CACHE = {}

        def present(name: str) -> bool:
            val = os.getenv(name)
            return val is not None and len(str(val).strip()) > 0

        # Build env summary (not cached: cheap and always current)
        env_summary = {
            "KIMI_API_KEY_present": present("KIMI_API_KEY"),
            "GLM_API_KEY_present": present("GLM_API_KEY"),
            "KIMI_API_URL": os.getenv("KIMI_API_URL", ""),
            "GLM_API_URL": os.getenv("GLM_API_URL", ""),
            "GLM_AGENT_API_URL": os.getenv("GLM_AGENT_API_URL", ""),
            "GLM_THINKING_MODE": os.getenv("GLM_THINKING_MODE", ""),
            "KIMI_ENABLE_INTERNET_TOOL": os.getenv("KIMI_ENABLE_INTERNET_TOOL", ""),
            "KIMI_DEFAULT_TOOL_CHOICE": os.getenv("KIMI_DEFAULT_TOOL_CHOICE", ""),
            "KIMI_DEFAULT_MODEL": os.getenv("KIMI_DEFAULT_MODEL", ""),
            "KIMI_FILES_MAX_SIZE_MB": os.getenv("KIMI_FILES_MAX_SIZE_MB", ""),
            "GLM_FILES_MAX_SIZE_MB": os.getenv("GLM_FILES_MAX_SIZE_MB", ""),
        }

        tools_list = []
        if include_tools:
            try:
                from tools.registry import ToolRegistry, TOOL_VISIBILITY
                _reg = ToolRegistry()
                _reg.build_tools()
                all_tools = _reg.list_tools()  # name -> instance
                # Default: only 'core' tools unless show_advanced=True
                visible = []
                for name in sorted(all_tools.keys()):
                    vis = TOOL_VISIBILITY.get(name, "core")
                    if vis == "core" or show_advanced:
                        visible.append(name)
                tools_list = visible
            except Exception:
                pass

        out = {"env": env_summary, "tools": tools_list, "showing_advanced": show_advanced}
        text = json.dumps(out, ensure_ascii=False)
        return [TextContent(type="text", text=text)]

