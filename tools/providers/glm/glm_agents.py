from __future__ import annotations

import os
import json
from typing import Any, Dict

import requests

from .shared.base_tool import BaseTool
from tools.shared.base_models import ToolRequest
from mcp.types import TextContent


def _glm_agent_base() -> str:
    return os.getenv("GLM_AGENT_API_URL", "https://api.z.ai/api/v1").rstrip("/")


def _glm_headers() -> Dict[str, str]:
    api_key = os.getenv("GLM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GLM_API_KEY is not configured")
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


class GLMAgentChatTool(BaseTool):
    def get_name(self) -> str:
        return "glm_agent_chat"

    def get_description(self) -> str:
        return "Call GLM Agent Chat endpoint (POST /v1/agents) with messages and optional custom_variables."

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent template id"},
                "messages": {"type": "array", "description": "OpenAI-style messages array"},
                "custom_variables": {"type": "object"},
                "stream": {"type": "boolean", "default": False},
            },
            "required": ["agent_id", "messages"],
        }

    def get_system_prompt(self) -> str:
        return (
            "You orchestrate GLM Agent Chat.\n"
            "Purpose: POST /v1/agents with agent_id, messages, optional custom_variables, and stream flag.\n\n"
            "Parameters:\n- agent_id: The target agent template id.\n- messages: OpenAI-style messages array.\n- custom_variables: Object of agent variables (optional).\n- stream: Whether to stream (false default).\n\n"
            "Notes:\n- Uses GLM_AGENT_API_URL and GLM_API_KEY for auth.\n- custom_variables are agent-defined; pass only fields required by the chosen agent template.\n- Keep payload minimal and privacy-preserving.\n\n"
            "Output: Return raw JSON as text for caller to parse (choices/status/ids)."
        )

    def get_request_model(self):
        return ToolRequest

    def requires_model(self) -> bool:
        return False

    async def prepare_prompt(self, request: ToolRequest) -> str:
        return ""

    def format_response(self, response: str, request: ToolRequest, model_info: dict | None = None) -> str:
        return response

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        url = f"{_glm_agent_base()}/agents"
        payload = {
            "agent_id": arguments["agent_id"],
            "messages": arguments["messages"],
            "stream": bool(arguments.get("stream", False)),
        }
        if "custom_variables" in arguments:
            payload["custom_variables"] = arguments["custom_variables"]
        r = requests.post(url, headers=_glm_headers(), data=json.dumps(payload), timeout=120)
        r.raise_for_status()
        return [TextContent(type="text", text=r.text)]


class GLMAgentGetResultTool(BaseTool):
    def get_name(self) -> str:
        return "glm_agent_get_result"

    def get_description(self) -> str:
        return "Retrieve async agent result (POST /v1/agents/result)."

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "async_id": {"type": "string"},
                "agent_id": {"type": "string"},
            },
            "required": ["async_id", "agent_id"],
        }

    def get_system_prompt(self) -> str:
        return (
            "You retrieve GLM Agent async results.\n"
            "Purpose: POST /v1/agents/result with async_id and agent_id to obtain the result.\n\n"
            "Parameters: async_id, agent_id.\n"
            "Output: Raw JSON as text (status/data). Keep payload minimal."
        )

    def get_request_model(self):
        return ToolRequest

    def requires_model(self) -> bool:
        return False

    async def prepare_prompt(self, request: ToolRequest) -> str:
        return ""

    def format_response(self, response: str, request: ToolRequest, model_info: dict | None = None) -> str:
        return response

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        url = f"{_glm_agent_base()}/agents/result"
        payload = {"async_id": arguments["async_id"], "agent_id": arguments["agent_id"]}
        r = requests.post(url, headers=_glm_headers(), data=json.dumps(payload), timeout=120)
        r.raise_for_status()
        return [TextContent(type="text", text=r.text)]


class GLMAgentConversationTool(BaseTool):
    def get_name(self) -> str:
        return "glm_agent_conversation"

    def get_description(self) -> str:
        return "Get agent conversation history (POST /v1/agents/conversation)."

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "conversation_id": {"type": "string"},
                "page": {"type": "integer", "default": 1},
                "page_size": {"type": "integer", "default": 20},
            },
            "required": ["agent_id", "conversation_id"],
        }

    def get_system_prompt(self) -> str:
        return (
            "You retrieve GLM Agent conversations.\n"
            "Purpose: POST /v1/agents/conversation with agent_id, conversation_id, page, page_size.\n\n"
            "Output: Raw JSON as text with conversation items."
        )

    def get_request_model(self):
        return ToolRequest

    def requires_model(self) -> bool:
        return False

    async def prepare_prompt(self, request: ToolRequest) -> str:
        return ""

    def format_response(self, response: str, request: ToolRequest, model_info: dict | None = None) -> str:
        return response

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        url = f"{_glm_agent_base()}/agents/conversation"
        payload = {
            "agent_id": arguments["agent_id"],
            "conversation_id": arguments["conversation_id"],
            "page": int(arguments.get("page", 1)),
            "page_size": int(arguments.get("page_size", 20)),
        }
        r = requests.post(url, headers=_glm_headers(), data=json.dumps(payload), timeout=120)
        r.raise_for_status()
        return [TextContent(type="text", text=r.text)]

