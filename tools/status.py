from __future__ import annotations

import json
import os
from typing import Any, Dict

from mcp.types import TextContent

from tools.shared.base_tool import BaseTool
from tools.shared.base_models import ToolRequest
from tools.registry import ToolRegistry


class StatusTool(BaseTool):
    def get_name(self) -> str:
        return "status"

    def get_description(self) -> str:
        return "Status + Hub: providers/models snapshot and (optional) compact menu/hub with suggested routes."

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tail_lines": {"type": "integer", "default": 30},
                "include_tools": {"type": "boolean", "default": False},
                "doctor": {"type": "boolean", "default": False},
                "probe": {"type": "boolean", "default": False},
                "menu": {"type": "boolean", "default": False, "description": "Return compact menu items (<=12) for MCP dropdown."},
                "hub": {"type": "boolean", "default": False, "description": "Return StatusHub menu and suggested routes."},
                "action": {"type": "string", "description": "Optional hub action to plan (e.g., analyze, review, debug, plan, test, refactor, secure, trace, precommit, logs, status, consensus, chat)"},
                "goal": {"type": "string", "description": "Optional user goal/notes for routing"},
            },
        }

    def get_system_prompt(self) -> str:
        return "Return a compact JSON status with next steps, or compact menu when menu=true, or a hub menu when hub=true."

    def get_request_model(self):
        return ToolRequest

    def requires_model(self) -> bool:
        return False

    async def prepare_prompt(self, request) -> str:
        """Not used since status tool doesn't call AI models - returns system status directly"""
        return ""

    async def execute(self, arguments: Dict[str, Any]) -> list[TextContent]:
        tail = int(arguments.get("tail_lines", 30))
        include_tools = bool(arguments.get("include_tools", False))

        # Provider summary
        try:
            from tools.provider_capabilities import ProviderCapabilitiesTool
            pc = ProviderCapabilitiesTool()
            pc_out = await pc.execute({"include_tools": include_tools})
            pc_json = json.loads(pc_out[0].text)
        except Exception:
            pc_json = {"env": {}, "tools": []}

        # Health tails
        try:
            from tools.health import HealthTool
            ht = HealthTool()
            h_out = await ht.execute({"tail_lines": tail})
            h_json = json.loads(h_out[0].text)
        except Exception:
            h_json = {"metrics_tail": [], "toolcalls_tail": []}

        # Friendly guidance
        guidance = []
        if not pc_json.get("env", {}).get("KIMI_API_KEY_present") and not pc_json.get("env", {}).get("GLM_API_KEY_present"):
            guidance.append("Set KIMI_API_KEY or GLM_API_KEY to enable model calls. Then run listmodels.")
        if not h_json.get("metrics_tail"):
            guidance.append("No recent metrics. Try calling chat or analyze to generate activity.")

        out = {
            "providers_configured": h_json.get("providers_configured", []),
            "models_available": h_json.get("models_available", []),
            "tools_loaded": pc_json.get("tools", []) if include_tools else [],
            "last_errors": [ln for ln in h_json.get("metrics_tail", []) if "error" in ln.lower()][-3:],
            "next_steps": guidance,
        }

        # Optional: return compact menu for MCP dropdown
        if bool(arguments.get("menu", False)):
            try:
                ui_profile = os.getenv("UI_PROFILE", "").strip().lower()
                if ui_profile == "compact":
                    from tools.registry import COMPACT_VISIBLE_TOOLS
                    out["menu"] = sorted(COMPACT_VISIBLE_TOOLS)
                else:
                    try:
                        from server import TOOLS as _TOOLS  # type: ignore
                        out["menu"] = sorted(list(_TOOLS.keys()))
                    except Exception:
                        out["menu"] = sorted(pc_json.get("tools", []))
            except Exception as e:
                out["menu_error"] = f"Failed to build menu: {e}"

        # Optional: return Hub menu and suggestions
        if bool(arguments.get("hub", False)):
            try:
                try:
                    from tools.registry import COMPACT_VISIBLE_TOOLS
                    base_menu = sorted(COMPACT_VISIBLE_TOOLS)
                except Exception:
                    base_menu = [
                        "chat","analyze","codereview","debug","refactor","testgen",
                        "planner","secaudit","precommit","tracer","consensus","status",
                    ]
                out["hub_menu"] = base_menu
                act = (arguments.get("action") or "").strip().lower()
                goal = (arguments.get("goal") or "").strip()
                suggestions = []
                # Direct action mapping when present
                if act:
                    route = act if act in base_menu else ("status" if act not in base_menu else act)
                    suggestions.append({"action": act, "route": route, "goal": goal})
                else:
                    g = goal.lower()
                    if any(k in g for k in ["consensus","compare","stances","debate"]):
                        suggestions.append({"action":"consensus","route":"consensus","why":"multi-model intent detected"})
                    elif any(k in g for k in ["debug","error","traceback","crash"]):
                        suggestions.append({"action":"debug","route":"debug","why":"debug intent detected"})
                    elif any(k in g for k in ["review","diff","pr "]):
                        suggestions.append({"action":"codereview","route":"codereview","why":"review intent detected"})
                    elif any(k in g for k in ["plan","tasks","roadmap","milestone","break down"]):
                        suggestions.append({"action":"planner","route":"planner","why":"planning intent detected"})
                    elif any(k in g for k in ["test","pytest","unit test","coverage"]):
                        suggestions.append({"action":"testgen","route":"testgen","why":"testing intent detected"})
                    elif any(k in g for k in ["refactor","simplify","cleanup","rename","extract"]):
                        suggestions.append({"action":"refactor","route":"refactor","why":"refactor intent detected"})
                    elif any(k in g for k in ["secure","security","owasp","vulnerability","xss","csrf","sql injection"]):
                        suggestions.append({"action":"secaudit","route":"secaudit","why":"security intent detected"})
                    elif any(k in g for k in ["trace","call graph","dependencies","execution path"]):
                        suggestions.append({"action":"tracer","route":"tracer","why":"tracing intent detected"})
                    elif any(k in g for k in ["precommit","pre-commit","lint","ruff","format","quality gates"]):
                        suggestions.append({"action":"precommit","route":"precommit","why":"precommit intent detected"})
                    else:
                        suggestions.append({"action":"analyze","route":"analyze","why":"default analysis route"})
                out["hub_suggestions"] = suggestions
            except Exception as e:
                out["hub_error"] = f"Failed to build hub: {e}"

        # Optional doctor mode: perform fast probes and add guidance
        if bool(arguments.get("doctor", False)):
            doctor = {"probes": {}, "advice": []}
            # Probe listmodels
            try:
                from tools.listmodels import ListModelsTool
                lm = ListModelsTool()
                lm_out = await lm.execute({})
                lm_json = json.loads(lm_out[0].text)
                doctor["probes"]["listmodels"] = True if lm_json else False
            except Exception as e:
                doctor["probes"]["listmodels"] = False
                doctor["advice"].append(f"listmodels failed: {e}")
            # Probe tiny chat (no external writes)
            if bool(arguments.get("probe", False)):
                try:
                    from tools.chat import ChatTool
                    ct = ChatTool()
                    c_out = await ct.execute({"messages": ["ping"], "model": os.getenv("DEFAULT_MODEL", "glm-4.5-flash")})
                    doctor["probes"]["chat"] = True if c_out and c_out[0].text else False
                except Exception as e:
                    doctor["probes"]["chat"] = False
                    doctor["advice"].append(f"chat probe failed: {e}")
            out["doctor"] = doctor

        return [TextContent(type="text", text=json.dumps(out, ensure_ascii=False))]

