"""Provider capability adapters for provider-native web search.

This module abstracts provider-specific tool schema injection and request normalization
for web search capabilities. It lets tools (e.g., Chat) enable web search uniformly
without hard-coding provider conditionals in tool code.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import os

from .base import ProviderType


@dataclass
class WebSearchSchema:
    tools: Optional[List[Dict[str, Any]]]
    tool_choice: Optional[Any]


class ProviderCapabilitiesBase:
    def __init__(self, provider_type: ProviderType):
        self.provider_type = provider_type

    def supports_websearch(self) -> bool:
        return False

    def get_websearch_tool_schema(self, config: Dict[str, Any]) -> WebSearchSchema:
        # Default: no tools
        return WebSearchSchema(tools=None, tool_choice=None)

    def normalize_request_options(self, config: Dict[str, Any]) -> Dict[str, Any]:
        # Default: no changes
        return {}


class KimiCapabilities(ProviderCapabilitiesBase):
    def __init__(self):
        super().__init__(ProviderType.KIMI)

    def supports_websearch(self) -> bool:
        return os.getenv("KIMI_ENABLE_INTERNET_SEARCH", "true").strip().lower() == "true"

    def get_websearch_tool_schema(self, config: Dict[str, Any]) -> WebSearchSchema:
        if not self.supports_websearch() or not config.get("use_websearch"):
            return WebSearchSchema(None, None)
        # OpenAI-compatible function calling schema
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Internet search",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            # Consider adding locale/safety if provider supports it
                        },
                        "required": ["query"],
                    },
                },
            }
        ]
        return WebSearchSchema(tools=tools, tool_choice="auto")


class GLMCapabilities(ProviderCapabilitiesBase):
    def __init__(self):
        super().__init__(ProviderType.GLM)

    def supports_websearch(self) -> bool:
        return os.getenv("GLM_ENABLE_WEB_BROWSING", "true").strip().lower() == "true"

    def get_websearch_tool_schema(self, config: Dict[str, Any]) -> WebSearchSchema:
        if not self.supports_websearch() or not config.get("use_websearch"):
            return WebSearchSchema(None, None)
        # GLM requires non-null web_search object in tool spec
        tools = [{"type": "web_search", "web_search": {}}]
        return WebSearchSchema(tools=tools, tool_choice="auto")


def get_capabilities_for_provider(ptype: ProviderType) -> ProviderCapabilitiesBase:
    if ptype == ProviderType.KIMI:
        return KimiCapabilities()
    if ptype == ProviderType.GLM:
        return GLMCapabilities()
    # Default: no-op capabilities
    return ProviderCapabilitiesBase(ptype)
