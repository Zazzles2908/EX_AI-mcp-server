from __future__ import annotations

from typing import Dict, List


class SuggestionEngine:
    def generate(self, context: Dict[str, object]) -> List[str]:
        suggestions: List[str] = []
        if context.get("has_images"):
            suggestions.append("Consider enabling multimodal analysis for images.")
        if context.get("long_context"):
            suggestions.append("Use long-context model or summarize older turns.")
        if not suggestions:
            suggestions.append("Try fast mode for quicker feedback.")
        return suggestions

