"""
Model resolver stub. Centralizes decisions about provider/model per tool.
Gated and import-safe; replace with full policy engine when ready.
"""
from __future__ import annotations
from typing import Optional

DEFAULT_MODEL = "glm-4.5-flash"

class ModelResolver:
    def resolve_for_tool(self, tool: str, requested: Optional[str] = None) -> str:
        """
        Decide which model to use for a given tool. Keep conservative defaults.
        """
        if requested:
            return requested
        # Example policy: keep chat/analysis on default fast manager
        return DEFAULT_MODEL

