"""Optional Zhipu (GLM) helpers without importing legacy providers.*

This module intentionally avoids importing from top-level providers.* to prevent
mixed-tree dependencies. It exposes safe, optional helpers that return None when
Zhipu SDK is unavailable.
"""
from __future__ import annotations

from typing import Any, Optional
import logging
import os

logger = logging.getLogger(__name__)


def get_client_or_none(api_key: Optional[str] = None):
    """Return a ZhipuAI SDK client if SDK is installed, else None.

    Args:
        api_key: Optional explicit API key. If not provided, pulls from env
                 GLM_API_KEY or ZHIPUAI_API_KEY.
    """
    try:
        from zhipuai import ZhipuAI  # type: ignore
    except Exception as e:
        logger.debug("zhipuai SDK not available: %s", e)
        return None

    key = api_key or os.getenv("GLM_API_KEY") or os.getenv("ZHIPUAI_API_KEY")
    if not key:
        logger.info("Zhipu client not created: missing GLM_API_KEY/ZHIPUAI_API_KEY")
        return None
    try:
        return ZhipuAI(api_key=key)
    except Exception as e:
        logger.warning("Failed to initialize ZhipuAI client: %s", e)
        return None


def upload_file_via_sdk(file_path: str, purpose: str = "agent") -> Optional[str]:
    """Upload a file using Zhipu SDK if available. Returns file_id or None.

    This is a thin helper for tools that prefer SDK path when present.
    """
    client = get_client_or_none()
    if client is None:
        return None
    try:
        # Try common variants across SDK versions
        if hasattr(client, "files") and hasattr(client.files, "upload"):
            with open(file_path, "rb") as f:
                res = client.files.upload(file=f, purpose=purpose)
        elif hasattr(client, "files") and hasattr(client.files, "create"):
            with open(file_path, "rb") as f:
                res = client.files.create(file=f, purpose=purpose)
        else:
            return None
        file_id = getattr(res, "id", None)
        if not file_id and hasattr(res, "model_dump"):
            data = res.model_dump()
            file_id = data.get("id") or data.get("data", {}).get("id")
        return str(file_id) if file_id else None
    except Exception as e:
        logger.warning("Zhipu SDK upload failed: %s", e)
        return None


__all__ = [
    "get_client_or_none",
    "upload_file_via_sdk",
]
