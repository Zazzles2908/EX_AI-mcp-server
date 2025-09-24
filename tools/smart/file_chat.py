"""
FileChatTool (advisory-only scaffold)
- Accepts files (paths) + prompt, normalizes into a messages array.
- No routing/provider changes; leaves execution to upstream chat tool.
- Registration remains gated; not wired by default.
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


class FileChatTool:
    def get_name(self) -> str:
        return "file_chat"

    def get_description(self) -> str:
        return "File chat (advisory-only): prepares messages from files; no routing changes."

    async def execute(self, arguments: Dict[str, Any]) -> List[TextContent]:  # pragma: no cover
        files = arguments.get("files") or []
        prompt = arguments.get("prompt") or ""
        msgs = [
            {"role": "system", "content": "FileChat advisory scaffold (no routing changes)"},
            {"role": "user", "content": f"Prompt: {prompt}"},
            {"role": "user", "content": f"Files: {files}"},
        ]
        return [TextContent(type="text", text=str({"status": "prepared", "messages": msgs}))]

