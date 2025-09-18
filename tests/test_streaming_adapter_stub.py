import asyncio
from streaming.streaming_adapter import MoonshotStreamingAdapter, ZaiStreamingAdapter


def test_streaming_adapters_yield_chunk():
    async def run():
        m = MoonshotStreamingAdapter()
        z = ZaiStreamingAdapter()
        chunks_m = [c async for c in m.iter_stream({"prompt": "hello world"})]
        chunks_z = [c async for c in z.iter_stream({"prompt": "hello world"})]
        return chunks_m, chunks_z

    chunks_m, chunks_z = asyncio.get_event_loop().run_until_complete(run())
    assert chunks_m and isinstance(chunks_m[0], str)
    assert chunks_z and isinstance(chunks_z[0], str)

