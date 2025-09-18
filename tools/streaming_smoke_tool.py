from __future__ import annotations

from typing import Optional
from streaming.streaming_adapter import (
    MoonshotStreamingAdapter,
    ZaiStreamingAdapter,
)


async def get_stream_first_chunk(provider: str, prompt: str) -> Optional[str]:
    """Return the first streamed chunk for a prompt using the provider adapter.

    This is an MVP smoke-tool to exercise the streaming path from within tools/.
    """
    adapter = MoonshotStreamingAdapter() if provider == "moonshot" else ZaiStreamingAdapter()
    async for chunk in adapter.iter_stream({"prompt": prompt}):
        return chunk
    return None

