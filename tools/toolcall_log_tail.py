from __future__ import annotations
import os, json
from typing import Any, Dict
from pathlib import Path

from mcp.types import TextContent
from tools.shared.base_tool import BaseTool


class ToolcallLogTail(BaseTool):
    def get_name(self) -> str:
        return "toolcall_log_tail"

    def get_description(self) -> str:
        return (
            "Return the last N tool-call events from EX_TOOLCALL_LOG_PATH JSONL file (sanitized)."
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "n": {"type": "integer", "default": 20, "minimum": 1, "maximum": 200},
                "path": {"type": "string", "description": "Optional override path"},
            },
        }

    def get_system_prompt(self) -> str:
        return "Return tool call log events in JSON format."

    def get_request_model(self):
        from tools.shared.base_models import ToolRequest
        return ToolRequest

    def requires_model(self) -> bool:
        return False

    async def prepare_prompt(self, request) -> str:
        return ""

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        n = int(arguments.get("n") or 20)
        p = arguments.get("path") or os.getenv("EX_TOOLCALL_LOG_PATH", "")
        if not p:
            return [TextContent(type="text", text=json.dumps({
                "status": "disabled",
                "reason": "EX_TOOLCALL_LOG_PATH not set",
            }))]
        try:
            lines: list[str] = []
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    lines.append(line.rstrip("\n"))
            tail = lines[-n:]
            events = [json.loads(x) for x in tail if x.strip()]
            return [TextContent(type="text", text=json.dumps({
                "status": "ok",
                "count": len(events),
                "events": events,
            }, ensure_ascii=False))]
        except FileNotFoundError:
            return [TextContent(type="text", text=json.dumps({
                "status": "not_found",
                "path": p,
            }))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({
                "status": "error",
                "error": str(e),
            }))]

