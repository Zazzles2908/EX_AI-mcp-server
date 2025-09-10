import asyncio
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional


DEFAULT_MAX_INFLIGHT = int(os.getenv("EXAI_WS_SESSION_MAX_INFLIGHT", "8"))


@dataclass
class Session:
    session_id: str
    created_at: float = field(default_factory=lambda: time.time())
    inflight: int = 0
    closed: bool = False
    max_inflight: int = DEFAULT_MAX_INFLIGHT
    sem: asyncio.BoundedSemaphore = field(default_factory=lambda: asyncio.BoundedSemaphore(DEFAULT_MAX_INFLIGHT))


class SessionManager:
    """Session tracker with per-session inflight quota enforcement."""

    def __init__(self) -> None:
        self._sessions: Dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def ensure(self, session_id: Optional[str]) -> Session:
        if not session_id:
            session_id = str(uuid.uuid4())
        async with self._lock:
            sess = self._sessions.get(session_id)
            if not sess:
                sess = Session(session_id=session_id)
                self._sessions[session_id] = sess
            return sess

    async def get(self, session_id: str) -> Optional[Session]:
        async with self._lock:
            return self._sessions.get(session_id)

    async def remove(self, session_id: str) -> None:
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def list_ids(self) -> list[str]:
        async with self._lock:
            return list(self._sessions.keys())

