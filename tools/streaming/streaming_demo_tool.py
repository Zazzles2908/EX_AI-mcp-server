from __future__ import annotations

from typing import Dict, Any

from streaming.streaming_adapter import MoonshotStreamingAdapter, ZaiStreamingAdapter


async def async_run_stream(prompt: str, provider: str = "moonshot", stream: bool = True) -> Dict[str, Any]:
    """Async-friendly streaming demo.
    - If stream=False, return deterministic fallback (no network)
    - If stream=True, yield first chunk via provider adapter without managing event loops here
    """
    if not stream:
        return {"provider": provider, "stream": False, "text": prompt.upper()[:50]}

    adapter = MoonshotStreamingAdapter() if provider == "moonshot" else ZaiStreamingAdapter()
    first = ""
    async for chunk in adapter.iter_stream({"prompt": prompt}):
        first = chunk
        break
    return {"provider": provider, "stream": True, "text": first}


def run_stream(prompt: str, provider: str = "moonshot", stream: bool = True) -> Dict[str, Any]:
    """Synchronous wrapper retained for legacy callers.
    NOTE: Prefer using async_run_stream in async contexts. This wrapper will only run when no event loop is active.
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop; safe to use asyncio.run
        return asyncio.run(async_run_stream(prompt=prompt, provider=provider, stream=stream))
    # A loop is already running; do not try to nest loops in sync context
    raise RuntimeError("run_stream called inside a running event loop; use async_run_stream instead")
