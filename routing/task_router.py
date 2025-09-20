"""DEPRECATED shim: use `src.core.agentic.task_router` instead.

This module now re-exports the canonical agentic router to avoid duplicate logic.
It will be removed after the migration window.
"""
from __future__ import annotations

import warnings as _warnings

# Emit a deprecation warning once per process
_warnings.warn(
    "routing.task_router is deprecated; import from src.core.agentic.task_router",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export canonical implementations
from src.core.agentic.task_router import (  # noqa: F401
    TaskType as TaskType,
    IntelligentTaskRouter as IntelligentTaskRouter,
)

__all__ = ["TaskType", "IntelligentTaskRouter"]
