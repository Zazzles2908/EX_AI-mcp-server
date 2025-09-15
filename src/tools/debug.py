"""Phase C shim: canonicalize DebugIssueTool import under src.tools.

New code should import from src.tools.debug. This module re-exports the
existing implementation from tools.debug without behavior changes.
"""

from tools.debug import DebugIssueTool  # re-export

__all__ = ["DebugIssueTool"]

