from __future__ import annotations

from typing import Any, Dict, List


class AdvancedContextManager:
    """256K-aware context optimizer (Phase E MVP).

    Strategy:
    - Preserve all system messages
    - Keep last 10 non-system messages
    - If over limit, drop middle content (placeholder for summarization)
    """

    def __init__(self) -> None:
        self.moonshot_limit = 256_000
        self.zai_limit = 128_000

    def _estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        text = " ".join([str(m.get("content", "")) for m in messages])
        return max(0, len(text) // 4)

    def optimize_context(self, messages: List[Dict[str, Any]], platform: str) -> List[Dict[str, Any]]:
        if not messages:
            return []
        limit = self.moonshot_limit if platform == "moonshot" else self.zai_limit
        if self._estimate_tokens(messages) <= limit:
            return messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]
        tail = non_system[-10:]
        # Placeholder: drop middle content; future: summarize middle
        optimized = system_msgs + tail
        return optimized

