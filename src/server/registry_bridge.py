"""Registry bridge scaffolding.

Purpose: decouple provider/model registry access behind a stable facade so
server.py can import from a single place when we thin it out in P2.
"""
from __future__ import annotations
from typing import Any

class RegistryBridge:
    def get_available_models(self) -> list[str]:
        try:
            from src.providers.registry import ModelProviderRegistry
            return ModelProviderRegistry.get_available_model_names()
        except Exception:
            return []

registry_bridge = RegistryBridge()

# Tools registry accessor (single source of truth for server.py)
def get_tools_dict() -> dict:
    """Build tools via ToolRegistry and return the dict of name->tool.
    Keeps server.py thin and avoids scattered imports.
    """
    from tools.registry import ToolRegistry  # local import to avoid hard deps at import time
    reg = ToolRegistry()
    reg.build_tools()
    return reg.list_tools()


