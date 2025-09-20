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
        return "Concise EXAI status: providers, models, and recent issues; friendly next steps. Alias for health/provider_capabilities."

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tail_lines": {"type": "integer", "default": 30},
                "include_tools": {"type": "boolean", "default": False},
                "doctor": {"type": "boolean", "default": False},
                "probe": {"type": "boolean", "default": False},
            },
        }

    def get_system_prompt(self) -> str:
        return "Return a compact JSON status with next steps."

    def get_request_model(self):
        return ToolRequest

    def requires_model(self) -> bool:
        return False

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

