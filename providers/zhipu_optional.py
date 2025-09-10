"""Optional ZhipuAI provider loader.

This module attempts to import the official ZhipuAI SDK if present.
If not installed, it gracefully falls back to OpenAI-compatible usage via GLM provider.

Use: from providers.zhipu_optional import get_zhipu_client_or_none
"""
from __future__ import annotations
from typing import Any

def get_zhipu_client_or_none(api_key: str, base_url: str | None = None, **kwargs) -> Any | None:
    try:
        from zhipuai import ZhipuAI
    except Exception:
        return None
    try:
        if base_url:
            return ZhipuAI(api_key=api_key, base_url=base_url)
        return ZhipuAI(api_key=api_key)
    except Exception:
        return None

