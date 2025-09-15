"""
ToolHub (adapter) - Unified tool manager facade.

Goal: provide a future-friendly wrapper around the existing ToolRegistry
with capability metadata and progressive disclosure, without breaking
existing imports. In Phase C we'll fully rename registry usage.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

try:
    # Use existing registry under the hood
    from tools.registry import ToolRegistry as _LegacyRegistry
except Exception:  # pragma: no cover
    _LegacyRegistry = None  # type: ignore


@dataclass
class ToolHub:
    _registry: Any = field(default=None)

    def __post_init__(self):
        if _LegacyRegistry is None:
            raise RuntimeError("Legacy ToolRegistry not available")
        self._registry = _LegacyRegistry()

    def build_tools(self) -> None:
        self._registry.build_tools()

    def list_tools(self) -> Dict[str, Any]:
        return self._registry.list_tools()

    # Capability metadata hook (future):
    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "progressive_disclosure": True,
            "capability_metadata": True,
            "chain_support": "planned",
        }

