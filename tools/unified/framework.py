from __future__ import annotations

from typing import Dict, Any, Callable


class BaseUnifiedTool:
    name: str = "base"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover (override)
        return context


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, BaseUnifiedTool] = {}

    def register(self, tool: BaseUnifiedTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseUnifiedTool:
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]


class ToolManager:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def invoke(self, name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        tool = self.registry.get(name)
        return tool.run(context)

