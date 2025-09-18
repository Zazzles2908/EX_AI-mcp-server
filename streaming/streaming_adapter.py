from __future__ import annotations

from typing import AsyncIterator, Dict, Any


class StreamingAdapter:
    """Minimal streaming adapter interface (Phase E MVP).

    Concrete adapters should wrap provider streaming APIs and yield token/text chunks.
    """

    async def iter_stream(self, request: Dict[str, Any]) -> AsyncIterator[str]:  # pragma: no cover
        yield ""


class MoonshotStreamingAdapter(StreamingAdapter):
    async def iter_stream(self, request: Dict[str, Any]) -> AsyncIterator[str]:
        # Placeholder: yield a single chunk for now
        yield request.get("prompt", "")[:50]


class ZaiStreamingAdapter(StreamingAdapter):
    async def iter_stream(self, request: Dict[str, Any]) -> AsyncIterator[str]:
        # Placeholder: yield a single chunk for now
        yield request.get("prompt", "")[:50]

