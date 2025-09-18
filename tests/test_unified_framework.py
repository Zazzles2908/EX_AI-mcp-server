from tools.unified.framework import BaseUnifiedTool, ToolRegistry, ToolManager


class EchoTool(BaseUnifiedTool):
    name = "echo"

    def run(self, context):
        return {"echo": context.get("msg", "")}


def test_tool_registry_and_manager():
    reg = ToolRegistry()
    reg.register(EchoTool())
    mgr = ToolManager(reg)
    out = mgr.invoke("echo", {"msg": "hi"})
    assert out["echo"] == "hi"

