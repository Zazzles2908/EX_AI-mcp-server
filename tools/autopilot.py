from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

from mcp.types import TextContent

from tools.shared.base_tool import BaseTool
from tools.shared.base_models import ToolRequest


class AutopilotTool(BaseTool):
    def get_name(self) -> str:
        return "autopilot"

    def get_description(self) -> str:
        return (
            "ORCHESTRATED FLOW - Intent-routed meta tool. Given a goal, it picks the right tool: "
            "consensus (if asked), else thinkdeep (deep), else analyze by default; also routes to "
            "debug/refactor/testgen/planner/secaudit/tracer/precommit/codereview when intent is detected."
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

    async def prepare_prompt(self, request) -> str:
        """Not used since autopilot tool orchestrates other tools without calling AI models directly"""
        return ""

    # --- Intent routing helpers ---
    def _detect_intent(self, goal: str) -> str:
        g = goal.lower()
        if any(k in g for k in ["consensus", "compare models", "multi-model", "stances", "for/against", "debate"]):
            return "consensus"
        if any(k in g for k in ["debug", "bug", "exception", "traceback", "crash", "investigate"]):
            return "debug"
        if any(k in g for k in ["review", "code review", "pr ", "pull request", "diff"]):
            return "codereview"
        if any(k in g for k in ["refactor", "clean up", "cleanup", "simplify", "rename", "extract"]):
            return "refactor"
        if any(k in g for k in ["test", "unit test", "pytest", "coverage", "write tests"]):
            return "testgen"
        if any(k in g for k in ["plan", "tasks", "roadmap", "milestone", "break down"]):
            return "planner"
        if any(k in g for k in ["security", "owasp", "vulnerability", "xss", "sql injection", "csrf"]):
            return "secaudit"
        if any(k in g for k in ["trace", "call graph", "dependencies", "flow", "execution path"]):
            return "tracer"
        if any(k in g for k in ["precommit", "pre-commit", "lint", "ruff", "format", "ci checks", "quality gates"]):
            return "precommit"
        if any(k in g for k in ["document", "docs", "docstring", "documentation"]):
            return "docgen"
        return "auto"

    async def _pick_available(self, preferred: List[str]) -> str:
        try:
            from tools.listmodels import ListModelsTool
            lm = ListModelsTool()
            out = await lm.execute({})  # type: ignore
            avail = set(json.loads(out[0].text)) if out and out[0].text else set()
            for m in preferred:
                if m in avail:
                    return m
        except Exception:
            pass
        return preferred[0]

    def _preferred_models(self) -> Tuple[List[str], List[str]]:
        preferred_kimi = [
            os.getenv("KIMI_THINKING_MODEL", "kimi-thinking-preview"),
            os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview"),
            "kimi-k2-0905-preview",
            "kimi-k2-turbo-preview",
        ]
        preferred_glm = [
            os.getenv("DEFAULT_MODEL", "glm-4.5-flash"),
            "glm-4.5-air",
            "glm-4.5",
        ]
        return preferred_kimi, preferred_glm

    async def execute(self, arguments: Dict[str, Any]) -> List[TextContent]:
        goal = (arguments.get("goal") or "").strip()
        depth = (arguments.get("depth") or "standard").strip().lower()
        override_model = arguments.get("model")

        if not goal:
            return [TextContent(type="text", text=json.dumps({"error": "missing goal"}))]

        # 1) Readiness: status doctor (uses EXAI MCP-style tools internally)
        try:
            from tools.status import StatusTool
            st = StatusTool()
            stat_out = await st.execute({"doctor": True})
            status_json = json.loads(stat_out[0].text)
        except Exception as e:
            status_json = {"error": f"status failed: {e}"}

        # 2) Determine intent and preferred model based on goal/depth and available models
        text_lc = goal.lower()
        wants_consensus = any(k in text_lc for k in ["consensus", "compare models", "multi-model", "stances", "for/against", "debate"])

        # Prefer Kimi for deep/extended reasoning; GLM flash for quick steps
        preferred_kimi = [
            os.getenv("KIMI_THINKING_MODEL", "kimi-thinking-preview"),
            os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview"),
            "kimi-k2-0905-preview",
            "kimi-k2-turbo-preview",
        ]
        preferred_glm = [
            os.getenv("DEFAULT_MODEL", "glm-4.5-flash"),
            "glm-4.5-air",
            "glm-4.5",
        ]

        def _pick_available(preferred: list[str]) -> str:
            try:
                from tools.listmodels import ListModelsTool
                lm = ListModelsTool()
                out = await lm.execute({})  # type: ignore
                avail = set(json.loads(out[0].text)) if out and out[0].text else set()
                for m in preferred:
                    if m in avail:
                        return m
            except Exception:
                pass
            return preferred[0]

        # 3) Plan (kept concise)
        plan = [
            "Clarify the goal",
            "Identify relevant files or modules",
        ]
        if wants_consensus:
            plan.append("Run consensus across selected models")
        elif depth == "deep":
            plan.append("Run thinkdeep for tradeoff/architecture reasoning")
        else:
            plan.append("Analyze or chat to gather insights")
        plan.append("Summarize next steps")

        outputs: Dict[str, Any] = {"status": status_json, "plan": plan, "actions": []}

        try:
            # 4) Choose tool and args
            if wants_consensus:
                # Build a small, sensible default panel with Kimi + GLM
                kimi_model = _pick_available(preferred_kimi)
                glm_model = _pick_available(preferred_glm)
                models_cfg = [
                    {"model": kimi_model, "stance": "neutral"},
                    {"model": glm_model, "stance": "neutral"},
                ]
                action = {
                    "tool": "consensus",
                    "args": {
                        "step": goal,
                        "step_number": 1,
                        "total_steps": len(models_cfg),
                        "next_step_required": True,
                        "findings": "Initial neutral analysis and plan to consult models",
                        "models": models_cfg,
                    },
                }
            elif depth == "deep":
                model = override_model or _pick_available(preferred_kimi)
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
                model = override_model or _pick_available(preferred_glm)
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

            # 5) Execute via server registry (in-process)
            from server import TOOLS as SERVER_TOOLS  # type: ignore
            tool_impl = SERVER_TOOLS.get(action["tool"])  # tool instance
            if tool_impl is None:
                outputs["actions"][-1]["error"] = "tool not found"
            else:
                res = await tool_impl.execute(action["args"])  # type: ignore
                try:
                    first_text = getattr(res[0], "text", None) or ""
                except Exception:
                    first_text = ""
                outputs["actions"][-1]["result"] = json.loads(first_text) if first_text else None
        except Exception as e:
            outputs["error"] = str(e)

        # 6) Summarize
        summary = {
            "goal": goal,
            "depth": depth,
            "routed_tool": outputs.get("actions", [{}])[-1].get("tool") if outputs.get("actions") else None,
            "next_suggestions": [
                "Refine relevant_files and rerun analyze/consensus",
                "Use codereview/refactor/testgen based on findings",
                "Call status(doctor:true, probe:true) if errors appear"
            ],
        }
        outputs["summary"] = summary

        return [TextContent(type="text", text=json.dumps(outputs, ensure_ascii=False))]

