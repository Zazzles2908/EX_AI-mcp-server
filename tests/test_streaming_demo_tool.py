from tools.streaming_demo_tool import run_stream


def test_streaming_demo_tool_modes():
    r1 = run_stream("hello", provider="moonshot", stream=False)
    assert r1["stream"] is False and r1["text"]
    r2 = run_stream("hello", provider="zai", stream=True)
    assert r2["stream"] is True and isinstance(r2["text"], str)

