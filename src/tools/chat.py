"""Phase C shim: canonicalize ChatTool import under src.tools.

New code should import from src.tools.chat. This module re-exports the
existing implementation from tools.chat without behavior changes.
"""

from tools.chat import ChatTool  # re-export

__all__ = ["ChatTool"]

