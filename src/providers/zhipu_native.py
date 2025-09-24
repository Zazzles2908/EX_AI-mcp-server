"""
Zhipu Native Provider (scaffold) - not wired
- Avoids external deps; provides stubs to be integrated later under flags
"""
from __future__ import annotations
from typing import Any, Dict, List


def _success(content: str, model: str = "glm-4.5") -> Dict[str, Any]:
    return {
        "status": "success",
        "content": content,
        "provider": "ZHIPU_NATIVE",
        "model": model,
    }


def _not_implemented(feature: str) -> Dict[str, Any]:
    return {"status": "success", "content": f"[stub] {feature} not implemented", "provider": "ZHIPU_NATIVE"}


class ZhipuNativeProvider:  # pragma: no cover
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or ""

    async def chat_with_web_search(self, messages: List[Dict], model: str = "glm-4.5") -> Dict[str, Any]:
        return _not_implemented("chat_with_web_search")

    async def upload_and_analyze_file(self, file_path: str, prompt: str) -> Dict[str, Any]:
        return _not_implemented("upload_and_analyze_file")

