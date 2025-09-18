from __future__ import annotations

from typing import Dict


def suggest_params(prompt: str) -> Dict[str, object]:
    p = (prompt or "").lower()
    has_images = any(k in p for k in ["image:", "![", "<img", "vision"])  # crude
    long_context = len(prompt) > 128_000 // 4  # align with router heuristic
    task_type = (
        "multimodal_reasoning" if has_images else ("long_context_analysis" if long_context else "code_generation")
    )
    return {"has_images": has_images, "long_context": long_context, "task_type": task_type}

