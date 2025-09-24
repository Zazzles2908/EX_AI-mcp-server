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

# Feature flags helper (prefers src.config.features.env_true, falls back to src.server.env)
def get_feature_flags() -> dict[str, bool]:
    try:
        from src.config.features import env_true  # type: ignore
        return {
            "ai_manager": env_true("ENABLE_AI_MANAGER"),
            "web_search": env_true("ENABLE_WEB_SEARCH"),
            "file_upload": env_true("ENABLE_FILE_UPLOAD"),
            "fallback": env_true("ENABLE_FALLBACK"),
        }
    except Exception:
        try:
            from src.server.env import env  # type: ignore
            return env.get_feature_flags()
        except Exception:
            return {"ai_manager": False, "web_search": False, "file_upload": True, "fallback": True}



