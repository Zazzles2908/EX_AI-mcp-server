from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from mcp.types import TextContent

from tools.shared.base_tool import BaseTool
from tools.shared.base_models import ToolRequest


class AutopilotTool(BaseTool):
    def get_name(self) -> str:
        return "autopilot"

    def get_description(self) -> str:
        return (
            "ORCHESTRATED FLOW - Given a goal, plan and execute a minimal sequence using existing tools: "
            "status → planner/thinkdeep (optional) → analyze/chat → validate → summarize. "
            "Routes simple steps to GLM flash and deep steps to Kimi thinking."
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "goal": {"type": "string", "description": "User goal in one or two sentences"},
                "depth": {"type": "string", "enum": ["quick", "standard", "deep"], "default": "standard"},
                "model": {"type": "string", "description": "Override model; otherwise use auto routing"},
            },
            "required": ["goal"],
        }

    def get_system_prompt(self) -> str:
        return "Plan minimal steps and call existing tools; keep outputs concise and actionable."

    def get_request_model(self):
        return ToolRequest

    def requires_model(self) -> bool:
        return False

    async def execute(self, arguments: Dict[str, Any]) -> List[TextContent]:
        goal = (arguments.get("goal") or "").strip()
        depth = (arguments.get("depth") or "standard").strip().lower()
        override_model = arguments.get("model")

        if not goal:
            return [TextContent(type="text", text=json.dumps({"error": "missing goal"}))]

        # 1) Readiness: status doctor
        try:
            from tools.status import StatusTool
            st = StatusTool()
            stat_out = await st.execute({"doctor": True})
            status_json = json.loads(stat_out[0].text)
        except Exception as e:
            status_json = {"error": f"status failed: {e}"}

        # 2) Plan
        plan = [
            "Clarify the goal",
            "Identify relevant files or modules",
            "Analyze or chat to gather insights",
            "Summarize next steps"
        ]
        if depth == "deep":
            plan.insert(2, "Run thinkdeep for tradeoff/architecture reasoning")

        # 3) Route and execute one minimal step
        outputs: Dict[str, Any] = {"status": status_json, "plan": plan, "actions": []}

        try:
            # Choose tool and model automatically
            if depth == "deep":
                model = override_model or os.getenv("KIMI_THINKING_MODEL", "kimi-thinking-preview")
                action = {
                    "tool": "thinkdeep",
                    "args": {
                        "step": goal,
                        "step_number": 1,
                        "total_steps": 1,
                        "next_step_required": False,
                        "findings": "",
                        "thinking_mode": "high",
                        "model": model,
                    },
                }
            else:
                # Quick analyze without explicit relevant_files to trigger git-aware default
                model = override_model or os.getenv("DEFAULT_MODEL", "glm-4.5-flash")
                action = {
                    "tool": "analyze",
                    "args": {
                        "step": goal,
                        "step_number": 1,
                        "total_steps": 1,
                        "next_step_required": True,
                        "findings": "Kickoff analysis",
                        "analysis_type": "general",
                        "model": model,
                    },
                }

            outputs["actions"].append(action)

            # Actually call the tool through our in-process registry
            from server import TOOLS as SERVER_TOOLS  # type: ignore
            tool_impl = SERVER_TOOLS.get(action["tool"])  # tool instance
            if tool_impl is None:
                outputs["actions"][-1]["error"] = "tool not found"
            else:
                res = await tool_impl.execute(action["args"])  # type: ignore
                # Try to return the first text content as string
                try:
                    first_text = getattr(res[0], "text", None) or ""
                except Exception:
                    first_text = ""
                outputs["actions"][-1]["result"] = json.loads(first_text) if first_text else None
        except Exception as e:
            outputs["error"] = str(e)

        # 4) Summarize
        summary = {
            "goal": goal,
            "depth": depth,
            "next_suggestions": [
                "Refine relevant_files and rerun analyze",
                "Use codereview/refactor/testgen based on findings",
                "Call status(doctor:true, probe:true) if errors appear"
            ],
        }
        outputs["summary"] = summary

        return [TextContent(type="text", text=json.dumps(outputs, ensure_ascii=False))]

