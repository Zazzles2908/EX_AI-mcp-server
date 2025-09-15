from __future__ import annotations

import json
from typing import Any, Dict

from mcp.types import TextContent

from tools.shared.base_tool import BaseTool
from tools.shared.base_models import ToolRequest
from utils.storage_backend import get_storage_backend


class AwaitResultTool(BaseTool):
    def get_name(self) -> str:
        return "await_result"

    def get_description(self) -> str:
        return "Fetch a deferred expert-analysis result by result_handle. Returns processing|complete|error|not_found."

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "result_handle": {"type": "string", "description": "Handle returned by a deferred workflow call"},
            },
            "required": ["result_handle"],
        }

    def get_system_prompt(self) -> str:
        return "Return the stored deferred result as raw JSON."

    def get_request_model(self):
        return ToolRequest

    def requires_model(self) -> bool:
        return False

    async def prepare_prompt(self, request) -> str:
        return ""

    async def execute(self, arguments: Dict[str, Any]) -> list[TextContent]:
        handle = (arguments.get("result_handle") or "").strip()
        storage = get_storage_backend()
        data = storage.get(f"deferred:{handle}") if handle else None
        if not data:
            payload = {"status": "not_found", "result_handle": handle}
        else:
            try:
                payload = json.loads(data)
                payload["result_handle"] = handle
            except Exception:
                payload = {"status": "error", "error": "Corrupt deferred payload", "raw": data, "result_handle": handle}
        return [TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))]

