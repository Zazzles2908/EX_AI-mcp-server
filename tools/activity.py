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
    since: Optional[str] = None   # ISO8601 datetime (flag-gated)
    until: Optional[str] = None   # ISO8601 datetime (flag-gated)
    structured: Optional[bool] = None  # JSONL output (flag-gated)


class ActivityTool(SimpleTool):
    name = "activity"
    description = (
        "MCP ACTIVITY VIEW - Returns recent server activity. Defaults to logs/mcp_activity.log, "
        "falls back to logs/mcp_server.log. Supports optional regex filtering and line count control."
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
            "source": {
                "type": "string",
                "enum": ["auto", "activity", "server"],
                "default": "auto",
                "description": "Which log to read: activity (mcp_activity.log), server (mcp_server.log), or auto (prefer activity then server)",
            },
            # Optional fields (flag-gated): we expose schema but behavior gated by flags
            "since": {
                "type": "string",
                "description": "Optional ISO8601 datetime to filter lines since this time (flag-gated)",
            },
            "until": {
                "type": "string",
                "description": "Optional ISO8601 datetime to filter lines until this time (flag-gated)",
            },
            "structured": {
                "type": "boolean",
                "description": "Optional JSONL output mode (flag-gated)",
                "default": False,
            },
        }

    def get_required_fields(self) -> list[str]:
        return []

    def get_system_prompt(self) -> str:
        return (
            "You surface recent MCP activity/server log lines with optional regex filtering.\n"
            "- Source can be 'activity' (mcp_activity.log), 'server' (mcp_server.log), or 'auto' (prefer activity then server).\n"
            "- Clamp line count to schema bounds; compile regex safely (on error, report).\n"
            "- Read safely with UTF-8 and errors=ignore; include rotation fallback when current file has too few lines.\n"
            "- Do not mask or transform content; return raw text lines.\n"
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

        # Determine project root
        project_root = Path(__file__).resolve().parents[1]

        # Decide source: 'activity' | 'server' | 'auto'
        source = str(arguments.get("source") or "auto").strip().lower()
        if source not in {"activity", "server", "auto"}:
            source = "auto"

        # Candidate paths with optional environment overrides
        act_override = os.getenv("EX_ACTIVITY_LOG_PATH", "").strip()
        srv_override = os.getenv("EX_SERVER_LOG_PATH", "").strip()

        def _expand(p: str) -> Path:
            import os.path
            return Path(os.path.abspath(os.path.expanduser(os.path.expandvars(p)))).resolve()
        act_path = _expand(act_override) if act_override else (project_root / "logs" / "mcp_activity.log").resolve()
        srv_path = _expand(srv_override) if srv_override else (project_root / "logs" / "mcp_server.log").resolve()

        # Select log path based on source with sensible fallbacks
        selected_path: Optional[Path] = None
        if source == "activity":
            selected_path = act_path
        elif source == "server":
            selected_path = srv_path
        else:  # auto
            if act_path.exists() and act_path.is_file() and act_path.stat().st_size > 0:
                selected_path = act_path
            elif srv_path.exists() and srv_path.is_file():
                selected_path = srv_path
            else:
                # Prefer activity path for error message
                selected_path = act_path

        # Safety: if using defaults (no override), keep within project; allow explicit overrides anywhere
        if not any([act_override, srv_override]):
            if not str(selected_path).startswith(str(project_root)):
                return [TextContent(type="text", text=f"[activity:error] Refusing to read outside project: {selected_path}")]

        if not selected_path.exists() or not selected_path.is_file():
            return [TextContent(type="text", text=f"[activity:error] Log file not found or inaccessible: {selected_path}")]

        # Clamp requested line count to schema bounds for safety
        try:
            n_requested = int(req.lines or 200)
        except Exception:
            n_requested = 200
        n = max(10, min(5000, n_requested))

        # Helper: read last n lines with rotation fallback for files like <name>.1, <name>.2 ...
        def read_tail_with_rotation(base_path: Path, n: int) -> list[str]:
            from collections import deque
            dq: deque[str] = deque(maxlen=n)
            base_dir = base_path.parent
            base_name = base_path.name

            # Collect rotated files (oldest first), then current
            rotated: list[Path] = []
            try:
                for p in base_dir.iterdir():
                    if p.name.startswith(base_name + "."):
                        try:
                            suffix = p.name.split(".")[-1]
                            idx = int(suffix)
                            rotated.append((idx, p))
                        except Exception:
                            continue
                rotated.sort(key=lambda t: t[0], reverse=True)  # highest index = oldest
            except Exception:
                rotated = []

            # Feed oldest -> newest (rotated high->low), then current
            for _, rp in rotated:
                try:
                    with rp.open("r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            dq.append(line)
                except Exception:
                    continue

            # Now current file
            try:
                with base_path.open("r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        dq.append(line)
            except Exception as e:
                raise e

            return list(dq)

        # Read tail with rotation
        try:
            tail = read_tail_with_rotation(selected_path, n)
        except Exception as e:
            return [TextContent(type="text", text=f"[activity:error] Failed to read log: {e}")]

        # Optional time window filtering (flag-gated)
        ACTIVITY_SINCE_UNTIL_ENABLED = os.getenv("ACTIVITY_SINCE_UNTIL_ENABLED", "false").strip().lower() == "true"
        if ACTIVITY_SINCE_UNTIL_ENABLED and (req.since or req.until):
            from datetime import datetime
            def parse_dt(s: str) -> Optional[datetime]:
                try:
                    return datetime.fromisoformat(s)
                except Exception:
                    return None
            since_dt = parse_dt(req.since) if req.since else None
            until_dt = parse_dt(req.until) if req.until else None
            filtered: list[str] = []
            for ln in tail:
                # Heuristic: parse timestamp at start of line if present; if absent, default to keep line
                ts = None
                # Prefer space-separated 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DDTHH:MM:SS'
                m = re.match(r"^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})", ln)
                if m:
                    ts = parse_dt(f"{m.group(1)}T{m.group(2)}")
                if ts is None:
                    # Keep non-timestamped lines to avoid accidental loss
                    filtered.append(ln)
                    continue
                if since_dt and ts < since_dt:
                    continue
                if until_dt and ts > until_dt:
                    continue
                filtered.append(ln)
            tail = filtered

        # Apply optional regex filter
        if req.filter:
            try:
                pattern = re.compile(req.filter)
                tail = [ln for ln in tail if pattern.search(ln)]
            except Exception as e:
                return [TextContent(type="text", text=f"[activity:error] Invalid filter regex: {e}")]

        # Optional structured output (flag-gated)
        ACTIVITY_STRUCTURED_OUTPUT_ENABLED = os.getenv("ACTIVITY_STRUCTURED_OUTPUT_ENABLED", "false").strip().lower() == "true"
        structured = bool(req.structured) if req.structured is not None else False
        if ACTIVITY_STRUCTURED_OUTPUT_ENABLED and structured:
            # Convert each line to a JSON record with minimal fields
            import json
            records = []
            for ln in tail[-n:]:
                records.append(json.dumps({"line": ln.rstrip("\n")}, ensure_ascii=False))
            jsonl = "\n".join(records)
            return [TextContent(type="text", text=jsonl)]

        # Return as plain text block with minimal formatting
        content = "".join(tail[-n:])
        return [TextContent(type="text", text=content)]

