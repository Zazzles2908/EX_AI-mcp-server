import os
import pytest

# This test ensures that when the server is imported and providers are configured,
# the registry exposes GLM models via MCP tool boundary.

def setup_module(module):
    # Ensure keys are present for the test environment; skip if missing
    if not os.getenv("GLM_API_KEY") and not os.getenv("KIMI_API_KEY"):
        pytest.skip("No provider API keys in environment; skipping provider bootstrap test")


def test_listmodels_shows_glm_when_key_present(monkeypatch):
    # Import server and configure providers via lazy guard
    import server

    # Ensure providers are configured if not already
    if hasattr(server, "configure_providers"):
        try:
            server.configure_providers()
        except Exception:
            pass

    from server import handle_call_tool

    # Call listmodels via MCP tool boundary (safe, no external completions)
    out_chunks = pytest.run(async_fn=lambda: handle_call_tool("listmodels", {}))

    # Fallback if async helper not available in test env
    if out_chunks is None:
        import asyncio
        out_chunks = asyncio.get_event_loop().run_until_complete(handle_call_tool("listmodels", {}))

    texts = [getattr(c, "text", getattr(c, "content", "")) for c in out_chunks]
    body = "\n".join([t for t in texts if isinstance(t, str)])

    # Basic assertions: GLM block present when GLM_API_KEY is set
    if os.getenv("GLM_API_KEY"):
        assert "ZhipuAI GLM" in body
        assert "✅" in body or "Models" in body
        # Heuristic: at least one glm-4.5-* string appears
        assert ("glm-4.5-air" in body) or ("glm-4.5-flash" in body) or ("glm-4.5" in body)
    # Kimi sanity if key present
    if os.getenv("KIMI_API_KEY"):
        assert "Moonshot Kimi" in body

