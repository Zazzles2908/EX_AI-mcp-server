"""
ActivityTool - Surface recent MCP activity/logs for visibility in clients

Returns recent lines from logs/mcp_server.log, optionally filtered.
Useful when client UI does not show per-step dropdowns.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.simple.base import SimpleTool
from tools.shared.base_models import ToolRequest


class ActivityRequest(ToolRequest):
    lines: Optional[int] = 200
    filter: Optional[str] = None  # regex


class ActivityTool(SimpleTool):
    name = "activity"
    description = (
        "MCP ACTIVITY VIEW - Returns recent server activity from logs/mcp_server.log. "
        "Supports optional regex filtering and line count control."
    )

    def get_name(self) -> str:
        return self.name

    def get_description(self) -> str:
        return self.description

    def get_model_category(self):
        from tools.models import ToolModelCategory
        return ToolModelCategory.FAST_RESPONSE

    def get_tool_fields(self) -> dict[str, dict[str, Any]]:
        return {
            "lines": {
                "type": "integer",
                "minimum": 10,
                "maximum": 5000,
                "default": 200,
                "description": "Number of log lines from the end of the file to return",
            },
            "filter": {
                "type": "string",
                "description": "Optional regex to filter lines (e.g., 'TOOL_CALL|CallToolRequest')",
            },
        }

    def get_required_fields(self) -> list[str]:
        return []

    def get_system_prompt(self) -> str:
        return (
            "You surface recent MCP server activity/log lines with optional regex filtering.\n"
            "- Clamp line count to schema bounds.\n- Compile regex safely; if invalid, report an error.\n- Do not attempt to mask or transform content; return raw text lines.\n"
        )

    async def prepare_prompt(self, request) -> str:
        return ""

    async def execute(self, arguments: Dict[str, Any]) -> List:
        from mcp.types import TextContent
        from tools.models import ToolOutput

        try:
            req = ActivityRequest(**arguments)
        except Exception as e:
            return [TextContent(type="text", text=f"[activity:error] {e}")]

        # Resolve log path safely within project boundary
        # 1) Allow explicit override via EX_ACTIVITY_LOG_PATH
        # 2) Default to <project_root>/logs/mcp_activity.log (activity-focused)
        override = os.getenv("EX_ACTIVITY_LOG_PATH", "").strip()
        if override:
            from os.path import expanduser, expandvars, abspath
            log_path = Path(abspath(expanduser(expandvars(override)))).resolve()
            project_root = Path.cwd().resolve()
        else:
            # Derive project root from this file (repo root)
            project_root = Path(__file__).resolve().parents[1]
            log_path = (project_root / "logs" / "mcp_activity.log").resolve()

        if not str(log_path).startswith(str(project_root)) or not log_path.exists() or not log_path.is_file():
            return [TextContent(type="text", text=f"[activity:error] Log file not found or inaccessible: {log_path}")]

        # Clamp requested line count to schema bounds for safety
        try:
            n_requested = int(req.lines or 200)
        except Exception:
            n_requested = 200
        n = max(10, min(5000, n_requested))

        # Stream tail efficiently without loading entire file
        try:
            from collections import deque
            tail_deque = deque(maxlen=n)
            with log_path.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    tail_deque.append(line)
            tail = list(tail_deque)
        except Exception as e:
            return [TextContent(type="text", text=f"[activity:error] Failed to read log: {e}")]

        if req.filter:
            try:
                pattern = re.compile(req.filter)
                tail = [ln for ln in tail if pattern.search(ln)]
            except Exception as e:
                return [TextContent(type="text", text=f"[activity:error] Invalid filter regex: {e}")]

        # Return as plain text block with minimal formatting
        content = "".join(tail[-n:])
        # Plain text across the board (no JSON wrapper) for better client rendering
        return [TextContent(type="text", text=content)]

