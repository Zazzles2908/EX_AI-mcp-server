"""Phase C shim: canonicalize PlannerTool import under src.tools.

New code should import from src.tools.planner. This module re-exports the
existing implementation from tools.planner without behavior changes.
"""

from tools.planner import PlannerTool  # re-export

__all__ = ["PlannerTool"]

