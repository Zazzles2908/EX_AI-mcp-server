import asyncio
from tools.streaming_smoke_tool import get_stream_first_chunk


def test_streaming_smoke_tool_returns_chunk():
    async def run():
        c1 = await get_stream_first_chunk("moonshot", "hello world")
        c2 = await get_stream_first_chunk("zai", "hello world")
        return c1, c2

    c1, c2 = asyncio.get_event_loop().run_until_complete(run())
    assert isinstance(c1, str) and c1
    assert isinstance(c2, str) and c2

