"""
Moonshot (Kimi) Native Provider (scaffold) - not wired
- Avoids external deps; provides stubs to be integrated later under flags
"""
from __future__ import annotations
from typing import Any, Dict, List


def _success(content: str, model: str = "kimi-k2-0905-preview") -> Dict[str, Any]:
    return {
        "status": "success",
        "content": content,
        "provider": "MOONSHOT_NATIVE",
        "model": model,
    }


def _not_implemented(feature: str) -> Dict[str, Any]:
    return {"status": "success", "content": f"[stub] {feature} not implemented", "provider": "MOONSHOT_NATIVE"}


class MoonshotNativeProvider:  # pragma: no cover
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.moonshot.ai/v1"):
        self.api_key = api_key or ""
        self.base_url = base_url

    async def file_based_qa(self, file_paths: List[str], question: str, model: str = "kimi-k2-0905-preview") -> Dict[str, Any]:
        return _not_implemented("file_based_qa")

    async def long_context_chat(self, messages: List[Dict], model: str = "kimi-k2-0905-preview") -> Dict[str, Any]:
        return _not_implemented("long_context_chat")

