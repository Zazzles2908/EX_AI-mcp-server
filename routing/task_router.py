from __future__ import annotations

# DEPRECATION SHIM: routing.task_router is deprecated.
# Use src.core.agentic.task_router instead. This module re-exports the canonical
# classes for backward compatibility during the migration window.
import warnings as _warnings

_warnings.warn(
    "routing.task_router is deprecated; import from src.core.agentic.task_router",
    DeprecationWarning,
    stacklevel=2,
)

from src.core.agentic.task_router import TaskType, IntelligentTaskRouter  # noqa: F401
