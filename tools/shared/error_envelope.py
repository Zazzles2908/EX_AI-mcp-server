from __future__ import annotations

from typing import Any, Dict


def make_error_envelope(provider: str, tool: str, error: BaseException | str, detail: str | None = None) -> Dict[str, Any]:
    """Create a standardized error envelope for tool failures.

    Shape:
      {
        "status": "execution_error",
        "error_class": "<exception-lower>" | "error",
        "provider": "KIMI|GLM|unknown",
        "tool": "<tool_name>",
        "detail": "<string>"
      }
    """
    if isinstance(error, BaseException):
        cls = type(error).__name__.lower()
        msg = str(error)
    else:
        cls = "error"
        msg = str(error)
    if detail:
        msg = f"{msg}"
    return {
        "status": "execution_error",
        "error_class": cls,
        "provider": provider or "unknown",
        "tool": tool or "unknown",
        "detail": msg,
    }

