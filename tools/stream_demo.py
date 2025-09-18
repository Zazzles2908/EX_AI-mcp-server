from __future__ import annotations

"""
Stream Demo MCP Tool

Purpose
- Demonstrate streaming behavior safely.
- If stream=False, return a deterministic fallback (no network) for stable tests.
- If stream=True, return the first streamed chunk using the provider adapter.

This is a utility tool and does not require an AI model.
"""
from typing import Any, Optional

from mcp.types import TextContent

from tools.shared.base_tool import BaseTool
from tools.shared.base_models import ToolRequest
from tools.models import ToolModelCategory, ToolOutput
from tools.streaming_demo_tool import async_run_stream


class StreamDemoTool(BaseTool):
    def get_name(self) -> str:
        return "stream_demo"

    def get_description(self) -> str:
        return (
            "STREAMING DEMONSTRATION — Returns either the first streamed chunk from a "
            "provider adapter (moonshot/zai) or a deterministic non-stream fallback."
        )

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Prompt to send to the streaming adapter or fallback",
                },
                "provider": {
                    "type": "string",
                    "enum": ["moonshot", "zai"],
                    "default": "moonshot",
                    "description": "Which adapter to use for streaming mode",
                },
                "stream": {
                    "type": "boolean",
                    "default": True,
                    "description": "If true, stream and return first chunk; if false, deterministic fallback",
                },
            },
            "required": ["prompt"],
        }

    def get_annotations(self) -> Optional[dict[str, Any]]:
        return {"readOnlyHint": True}

    def get_system_prompt(self) -> str:
        return ""

    def get_request_model(self):
        # No complex validation needed; ToolRequest covers minimal structure
        return ToolRequest

    def requires_model(self) -> bool:
        return False

    async def prepare_prompt(self, request: ToolRequest) -> str:
        return ""

    def format_response(self, response: str, request: ToolRequest, model_info: dict | None = None) -> str:
        return response

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        prompt: str = arguments.get("prompt", "").strip()
        provider: str = (arguments.get("provider") or "moonshot").strip().lower()
        stream: bool = bool(arguments.get("stream", True))

        if not prompt:
            raise ValueError("'prompt' is required")
        if provider not in {"moonshot", "zai"}:
            provider = "moonshot"

        result = await async_run_stream(prompt=prompt, provider=provider, stream=stream)
        tool_output = ToolOutput(
            status="success",
            content=f"stream_demo result: {result}",
            content_type="text",
            metadata={"provider": provider, "stream": stream},
        )
        return [TextContent(type="text", text=tool_output.model_dump_json())]

    def get_model_category(self) -> ToolModelCategory:
        return ToolModelCategory.FAST_RESPONSE

