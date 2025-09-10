import os
import asyncio
import pytest

from server import handle_call_tool


def set_env(**kwargs):
    for k, v in kwargs.items():
        os.environ[k] = v


@pytest.mark.asyncio
async def test_orchestrate_auto_dry_run_no_model():
    set_env(HIDDEN_MODEL_ROUTER_ENABLED="true", ROUTER_SENTINEL_MODELS="glm-4.5-flash,auto")
    res = await handle_call_tool("orchestrate_auto", {"user_prompt": "Survey repo", "dry_run": True})
    assert isinstance(res, list) and len(res) > 0


@pytest.mark.asyncio
async def test_analyze_sentinel_routed(caplog):
    import logging
    set_env(HIDDEN_MODEL_ROUTER_ENABLED="true", ROUTER_SENTINEL_MODELS="glm-4.5-flash,auto")

    caplog.set_level(logging.INFO)

    args = {
        "step": "Plan",
        "step_number": 1,
        "total_steps": 1,
        "next_step_required": False,
        "findings": "",
        "model": "glm-4.5-flash",  # sentinel
        "relevant_files": [],
    }

    try:
        await handle_call_tool("analyze", args)
    except Exception:
        pass

    # Look for structured boundary selection log
    found = False
    for rec in caplog.records:
        msg = rec.msg
        if isinstance(msg, dict) and msg.get("event") == "boundary_model_resolved":
            found = True
            break
        # Also check stringified dict
        if isinstance(msg, str) and "boundary_model_resolved" in msg:
            found = True
            break

    assert found, "Expected boundary_model_resolved event in logs when sentinel is used"

    args = {
        "step": "Plan",
        "step_number": 1,
        "total_steps": 1,
        "next_step_required": False,
        "findings": "",
        "model": "glm-4.5-flash",  # sentinel
        "relevant_files": [],
    }
    try:
        await handle_call_tool("analyze", args)
    except Exception:
        # It's OK if provider keys are missing; we only care that routing occurred
        pass
    assert calls["resolve"] >= 1


@pytest.mark.asyncio
async def test_consensus_injects_model_context(monkeypatch):
    # Minimal test: ensure _consult_model can be called without raising missing model context
    from tools.consensus import ConsensusTool

    tool = ConsensusTool()

    # Mock provider to avoid real API calls
    class DummyProvider:
        def generate_content(self, prompt, model_name, **kwargs):
            class R:
                content = "ok"
            return R()
        def get_provider_type(self):
            class T:
                value = "dummy"
            return T()

    monkeypatch.setattr(tool, "get_model_provider", lambda model_name: DummyProvider())

    # Prepare request-like object
    class Req:
        relevant_files = []
        images = None
    req = Req()

    out = await tool._consult_model({"model": "kimi-k2-0905", "stance": "neutral"}, req)
    assert out["status"] == "success"
