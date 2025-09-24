"""
Minimal MCP protocol utilities (normalization helpers).
Import-safe; does not bind to a specific framework.
"""
from __future__ import annotations
from typing import Any, Dict


def normalize_chat_message(role: str, content: Any) -> Dict[str, Any]:
    """Ensure a consistent chat message shape."""
    return {"role": role, "content": content}


def ensure_messages(input_obj: Any) -> list[Dict[str, Any]]:
    """Convert common inputs into a messages array."""
    if isinstance(input_obj, list):
        return input_obj  # assume already in messages shape
    return [normalize_chat_message("user", input_obj)]

