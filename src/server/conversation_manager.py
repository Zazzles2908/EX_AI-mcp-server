"""
In-memory thread/continuation store for MCP server.
Thread-safe, no external persistence, minimal dependencies.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from collections import deque
from typing import Dict, List

MAX_THREAD_MESSAGES = int(os.getenv("MAX_THREAD_MESSAGES", "50"))


class ConversationManager:
    """Thread-safe in-memory conversation store with pruning."""

    def __init__(self) -> None:
        self._store: Dict[str, deque[dict]] = {}
        self._lock = asyncio.Lock()

    async def save(self, thread_id: str, messages: List[dict]) -> None:
        """Save messages for a thread, pruning to MAX_THREAD_MESSAGES."""
        async with self._lock:
            if thread_id not in self._store:
                self._store[thread_id] = deque(maxlen=MAX_THREAD_MESSAGES)
            dq = self._store[thread_id]
            dq.extend(messages)
            # Ensure we never exceed maxlen (defensive)
            while len(dq) > MAX_THREAD_MESSAGES:
                dq.popleft()

    async def load(self, thread_id: str) -> List[dict]:
        """Load messages for a thread; returns empty list if not found."""
        async with self._lock:
            dq = self._store.get(thread_id)
            return list(dq) if dq else []

    def get_cont_id(self) -> str:
        """Return a short random continuation ID (12 chars)."""
        return uuid.uuid4().hex[:12]


# Singleton instance
conversation_manager = ConversationManager()

