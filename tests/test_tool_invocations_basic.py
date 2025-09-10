import os
import pytest

from tools.registry import ToolRegistry


def build_registry():
    reg = ToolRegistry()
    reg.build_tools()
    return reg


def test_browse_orchestrator_dryrun_exec():
    reg = build_registry()
    tool = reg.get_tool("browse_orchestrator")
    # Call run() directly to avoid BaseTool async/transport glue
    out = tool.run(query="site:docs.python.org typing generics", dry_run=True)
    assert isinstance(out, dict)
    assert out.get("dry_run") is True
    assert isinstance(out.get("plan"), list)


def test_health_exec_returns_models_and_providers():
    reg = build_registry()
    tool = reg.get_tool("health")
    out = tool.run(tail_lines=5)
    assert isinstance(out, dict)
    assert "providers_configured" in out
    assert "models_available" in out


def test_conformance_descriptors_present_for_core_tools():
    reg = build_registry()
    for name in [
        "consensus",
        "orchestrate_auto",
        "kimi_chat_with_tools",
        "kimi_upload_and_extract",
        "secaudit",
        "testgen",
    ]:
        tool = reg.get_tool(name)
        desc = tool.get_descriptor()
        assert isinstance(desc, dict)
        # input_schema shape should be present even if tool validates args later
        assert isinstance(desc.get("input_schema"), dict)


@pytest.mark.skipif(not os.getenv("KIMI_API_KEY"), reason="Requires KIMI_API_KEY to call provider")
def test_kimi_chat_with_tools_minimal_descriptor_only():
    # Keep this minimal to avoid provider side-effects in CI; presence indicates conformance
    reg = build_registry()
    tool = reg.get_tool("kimi_chat_with_tools")
    desc = tool.get_descriptor()
    assert isinstance(desc, dict)

