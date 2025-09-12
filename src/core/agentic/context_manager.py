from __future__ import annotations

from typing import Any, Dict, List


class AdvancedContextManager:
    """256K-aware context optimization scaffolding.

    Strategies: preserve system messages, keep recent messages, compress middle.
    No external calls; compression is stubbed for now.
    """

    def __init__(self) -> None:
        self.moonshot_limit = 256_000
        self.zai_limit = 128_000

    def estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        total_chars = sum(len(m.get("content", "")) for m in messages if isinstance(m, dict))
        return total_chars // 4

    def optimize(self, messages: List[Dict[str, Any]], platform: str) -> List[Dict[str, Any]]:
        limit = self.moonshot_limit if platform == "moonshot" else self.zai_limit
        if self.estimate_tokens(messages) <= limit:
            return messages
        # Preserve system + last 10; stub compression for the middle
        system_msgs = [m for m in messages if m.get("role") == "system"]
        recent = messages[-10:]
        middle = [m for m in messages if m not in system_msgs][-10:]
        compressed_middle = self._compress_stub(middle)
        return system_msgs + compressed_middle + recent

    def _compress_stub(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Replace long contents with a short placeholder indicating compression
        out: List[Dict[str, Any]] = []
        for m in messages:
            content = m.get("content", "")
            if len(content) > 2000:
                out.append({**m, "content": f"[compressed {len(content)} chars]"})
            else:
                out.append(m)
        return out

