"""
SmartChatTool (advisory-only scaffold)
- Reads AI Manager advisory plan when enabled
- Does NOT alter routing or provider selection (no-op)
- Registration is gated elsewhere (ENABLE_SMART_CHAT=false by default)
"""
from __future__ import annotations

from typing import Any, Dict, List

try:
    from mcp.types import TextContent
except Exception:  # minimal shim for editor/test discovery
    class TextContent:  # type: ignore
        def __init__(self, type: str, text: str):
            self.type = type
            self.text = text


class SmartChatTool:
    def get_name(self) -> str:
        return "smart_chat"

    def get_description(self) -> str:
        return "Smart chat (advisory-only): logs manager plan; no routing changes."

    async def execute(self, arguments: Dict[str, Any]) -> List[TextContent]:  # pragma: no cover
        # Advisory-only message to indicate scaffold behavior
        msg = {
            "status": "success",
            "content": "SmartChat advisory scaffold active (no routing changes)",
            "tool": "chat",
        }
        return [TextContent(type="text", text=str(msg))]

