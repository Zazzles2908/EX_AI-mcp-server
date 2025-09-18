from __future__ import annotations

from typing import Dict


def select_mode(params: Dict[str, object]) -> str:
    if params.get("has_images"):
        return "balanced"
    if params.get("long_context"):
        return "deep"
    return "fast"

