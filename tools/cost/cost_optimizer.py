from __future__ import annotations

from typing import Dict


def choose_model(params: Dict[str, object]) -> str:
    """Return provider:model selection string based on simple rules.

    - Multimodal -> zai:glm-4v (vision)
    - Long context -> moonshot:kimi-k2-0711-preview (256k)
    - Default -> zai:glm-4.5-flash
    """
    if params.get("has_images"):
        return "zai:glm-4v"
    if params.get("long_context"):
        return "moonshot:kimi-k2-0711-preview"
    return "zai:glm-4.5-flash"

