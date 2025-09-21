from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from tools.shared.base_tool import BaseTool
from src.providers.registry import ModelProviderRegistry


class HealthTool(BaseTool):
    name = "health"
    description = "Report MCP/Provider health: configured providers, available models, and recent observability log tails."

    # BaseTool abstract requirements
    def get_name(self) -> str:
        return self.name

    def get_description(self) -> str:
        return self.description

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tail_lines": {"type": "integer", "default": 50},
            },
        }

    def get_system_prompt(self) -> str:
        return (
            "You summarize MCP server health. Return providers_configured, models_available, and JSONL tails.\n"
            "Keep output compact."
        )

    def get_request_model(self):
        # This tool does not use a Pydantic request model; pass-through dict
        from tools.shared.base_models import ToolRequest
        return ToolRequest

    async def prepare_prompt(self, request):  # pragma: no cover - not used
        return ""

    def get_descriptor(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "input_schema": self.get_input_schema(),
        }

    def _tail_file(self, path: Path, n: int) -> List[str]:
        try:
            if not path.exists():
                return []
            # Simple, small-tail reader (files are expected to be small-local JSONL)
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                return [ln.rstrip("\n") for ln in lines[-n:]]
        except Exception:
            return []

    def run(self, **kwargs) -> Dict[str, Any]:
        tail_lines = int(kwargs.get("tail_lines") or 50)

        providers_with_keys = ModelProviderRegistry.get_available_providers_with_keys()
        model_names = ModelProviderRegistry.get_available_model_names()

        # Observability log tails
        metrics_path = Path(os.getenv("EX_METRICS_LOG_PATH", ".logs/metrics.jsonl"))
        toolcalls_path = Path(os.getenv("EX_TOOLCALL_LOG_PATH", ".logs/toolcalls.jsonl"))

        metrics_tail = self._tail_file(metrics_path, tail_lines)
        toolcalls_tail = self._tail_file(toolcalls_path, tail_lines)

        return {
            "providers_configured": sorted([str(p) for p in providers_with_keys]),
            "models_available": sorted(model_names),
            "metrics_tail": metrics_tail,
            "toolcalls_tail": toolcalls_tail,
        }



    def requires_model(self) -> bool:
        """Health checks do not require model access."""
        return False

    async def execute(self, arguments: Dict[str, Any]) -> list:
        """Execute health check and return JSON text content.

        We avoid model resolution and simply return a compact JSON payload with
        providers configured, available models (names only), and short log tails.
        """
        import json
        from mcp.types import TextContent

        try:
            result = self.run(**(arguments or {}))
            text = json.dumps(result, ensure_ascii=False)
            return [TextContent(type="text", text=text)]
        except Exception as e:
            err = {"status": "error", "error": str(e)}
            return [TextContent(type="text", text=json.dumps(err, ensure_ascii=False))]
