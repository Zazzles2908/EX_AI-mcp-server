"""
Lightweight model metadata for intelligent selection (env-gated).
- Enabled when ENABLE_METADATA_SELECTION=true
- Can be overridden by providing MODEL_METADATA_JSON pointing to a JSON file
  with the same structure as MODEL_METADATA below.
"""
from __future__ import annotations
import json
import os
from typing import Any, Dict

# Minimal seed metadata (extend via env JSON)
MODEL_METADATA: Dict[str, Dict[str, Any]] = {
    # GLM
    "glm-4.5": {"category_hint": "EXTENDED_REASONING", "tier": "quality", "modalities": ["text"], "notes": "Higher-quality reasoning"},
    "glm-4.5-flash": {"category_hint": "FAST_RESPONSE", "tier": "speed", "modalities": ["text"], "notes": "Fast/cost-effective"},
    "glm-4.5-air": {"category_hint": "FAST_RESPONSE", "tier": "speed", "modalities": ["text"], "notes": "Fast variant"},
    # Kimi (normalize to canonical names; keep previews as internal only if truly supported)
    "kimi-k2": {"category_hint": "EXTENDED_REASONING", "tier": "quality", "modalities": ["text"], "notes": "Strong reasoning; good for CJK"},
    "kimi-k2-turbo": {"category_hint": "FAST_RESPONSE", "tier": "speed", "modalities": ["text"], "notes": "Fast/cost-effective"},
}

_loaded_env = False

def _load_env_json_once() -> None:
    """One-time load of MODEL_METADATA_JSON override if provided."""
    global _loaded_env
    if _loaded_env:
        return
    _loaded_env = True
    path = os.getenv("MODEL_METADATA_JSON")
    if not path:
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                MODEL_METADATA.update(data)
    except Exception:
        # Non-fatal; ignore malformed overrides
        pass


def get_model_metadata(name: str) -> Dict[str, Any]:
    _load_env_json_once()
    return MODEL_METADATA.get(name, {})
