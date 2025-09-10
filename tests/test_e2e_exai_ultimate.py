import os
import asyncio
import json
import logging
import pytest

from server import handle_call_tool, TOOLS

# Helper to set env flags used by hidden router

def set_router_env():
    os.environ["HIDDEN_MODEL_ROUTER_ENABLED"] = "true"
    os.environ["ROUTER_SENTINEL_MODELS"] = "glm-4.5-flash,auto"
    # DEFAULT_MODEL often used by tools when model missing
    os.environ["DEFAULT_MODEL"] = "glm-4.5-flash"


def assert_with_fix(condition: bool, message: str, fix: str):
    assert condition, f"{message}\nDirect Fix: {fix}"


@pytest.mark.asyncio
async def test_orchestrate_auto_dry_run_visible_plan():
    """EX-AI can plan without explicit model selection."""
    set_router_env()
    res = await handle_call_tool(
        "orchestrate_auto",
        {"user_prompt": "Quick architecture survey of this repo", "dry_run": True},
    )
    assert_with_fix(
        isinstance(res, list) and len(res) > 0,
        "orchestrate_auto returned no content in dry_run mode",
        "Ensure orchestrate_auto tool is registered and does not require 'model' when router is enabled.",
    )


@pytest.mark.asyncio
async def test_hidden_router_boundary_attempt_log(caplog):
    """Sentinel model triggers a boundary resolution attempt log."""
    set_router_env()
    caplog.set_level(logging.INFO)
    args = {
        "step": "Plan",
        "step_number": 1,
        "total_steps": 1,
        "next_step_required": False,
        "findings": "",
        "model": "auto",  # auto triggers boundary path
        "relevant_files": [],
    }
    try:
        await handle_call_tool("analyze", args)
    except Exception:
        # Provider availability not required for this check
        pass

    found_attempt = any(
        isinstance(r.msg, dict) and r.msg.get("event") == "boundary_model_resolution_attempt"
        or (isinstance(r.msg, str) and "boundary_model_resolution_attempt" in r.msg)
        for r in caplog.records
    )
    assert_with_fix(
        found_attempt,
        "No boundary_model_resolution_attempt event observed when using sentinel model",
        "Ensure server.py logs boundary_model_resolution_attempt before calling resolve_auto_model and that HIDDEN_MODEL_ROUTER_ENABLED=true.",
    )


@pytest.mark.asyncio
async def test_hidden_router_boundary_resolved_log_with_mock(monkeypatch, caplog):
    """When resolve_auto_model returns a concrete model, we log boundary_model_resolved."""
    set_router_env()
    caplog.set_level(logging.INFO)

    # Monkeypatch resolve_auto_model to force resolution
    import server as _server

    def fake_resolve(args, tool):  # noqa: ARG001
        return "glm-4"

    # Prefer the module-level function if present
    # Prefer the module-level override hook
    monkeypatch.setattr(_server, "_resolve_auto_model", fake_resolve)
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

    found_resolved = any(
        isinstance(r.msg, dict) and r.msg.get("event") == "boundary_model_resolved"
        or (isinstance(r.msg, str) and "boundary_model_resolved" in r.msg)
        for r in caplog.records
    )
    assert_with_fix(
        found_resolved,
        "No boundary_model_resolved event observed when resolve_auto_model returns a model",
        "Ensure server.py logs boundary_model_resolved after selecting a model and updating arguments['model'].",
    )


def test_schema_does_not_require_model_when_router_enabled():
    """Schemas for key tools should not require 'model' under hidden router mode."""
    set_router_env()
    # Only check tools that exist in this instance
    for name in ["analyze", "chat", "codereview"]:
        tool = TOOLS.get(name)
        if not tool:
            continue
        schema = tool.get_input_schema()
        req = set(schema.get("required") or [])
        assert_with_fix(
            "model" not in req,
            f"Tool '{name}' schema still requires 'model' under router mode",
            "Update BaseTool to relax model requirement when HIDDEN_MODEL_ROUTER_ENABLED=true and DEFAULT_MODEL is a sentinel.",
        )


@pytest.mark.asyncio
async def test_consensus_per_step_model_context_with_files(monkeypatch):
    """Consensus consultation should not error for file prep (ModelContext injected)."""
    set_router_env()
    from tools.consensus import ConsensusTool

    tool = ConsensusTool()

    # Create a small context file in project-local .tmp to avoid Windows temp perms
    base = os.path.join(os.getcwd(), ".tmp")
    os.makedirs(base, exist_ok=True)
    p = os.path.join(base, "ctx.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write("Hello context")

    # Dummy provider to avoid network calls
    class DummyProvider:
        def generate_content(self, prompt, model_name, **kwargs):  # noqa: ARG002
            class R:
                content = "ok"
            return R()

        def get_provider_type(self):
            class T:
                value = "dummy"
            return T()

    monkeypatch.setattr(tool, "get_model_provider", lambda model_name: DummyProvider())

    tool.initial_prompt = "Test proposal"

    class Req:
        relevant_files = [str(p)]
        images = None

    out = await tool._consult_model({"model": "kimi-k2-0905", "stance": "neutral"}, Req())
    assert_with_fix(
        out.get("status") == "success",
        "Consensus _consult_model did not complete successfully with relevant_files present",
        "Ensure ConsensusTool injects a per-step ModelContext before file preparation.",
    )


@pytest.mark.asyncio
async def test_tool_call_visibility_logs(caplog):
    """Server must emit tool-call visibility logs for observability."""
    caplog.set_level(logging.INFO)
    await handle_call_tool("version", {})

    found = any(
        isinstance(r.msg, str) and r.msg.startswith("TOOL_CALL:")
        for r in caplog.records
    )
    assert_with_fix(
        found,
        "TOOL_CALL visibility log not observed for 'version'",
        "Ensure server emits TOOL_CALL logs (and ToolOutput metadata if applicable).",
    )


def test_allowlist_models_are_canonical():
    """All models in .env allowlists must exist as canonical or alias names in providers."""
    from providers.kimi import KimiModelProvider
    from providers.glm import GLMModelProvider
    from providers.base import ProviderType

    # Build canonical+alias sets
    kimi_canon = set(KimiModelProvider.SUPPORTED_MODELS.keys())
    kimi_alias = set(a for caps in KimiModelProvider.SUPPORTED_MODELS.values() for a in caps.aliases)
    glm_canon = set(GLMModelProvider.SUPPORTED_MODELS.keys())
    glm_alias = set(a for caps in GLMModelProvider.SUPPORTED_MODELS.values() for a in caps.aliases)

    def check_env(var, canon, alias):
        raw = os.getenv(var, "")
        if not raw:
            return []
        invalid = []
        for m in [x.strip() for x in raw.split(",") if x.strip()]:
            if m not in canon and m not in alias:
                invalid.append(m)
        return invalid

    bad_kimi = check_env("KIMI_ALLOWED_MODELS", kimi_canon, kimi_alias)
    bad_glm = check_env("GLM_ALLOWED_MODELS", glm_canon, glm_alias)

    fix_text = (
        "Normalize .env allowlists to provider canonical IDs/aliases. For KIMI use one of: "
        f"{sorted(list(kimi_canon | kimi_alias))}. For GLM use one of: {sorted(list(glm_canon | glm_alias))}."
    )

    assert_with_fix(
        not bad_kimi and not bad_glm,
        f"Invalid models in allowlists. KIMI: {bad_kimi} GLM: {bad_glm}",
        fix_text,
    )

