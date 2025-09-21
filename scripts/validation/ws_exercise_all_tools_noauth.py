#!/usr/bin/env python
"""Wrapper copy under scripts/validation to exercise WS tools with no token.
Supports both local package-style import and fallback to same-folder import.
"""
import os, asyncio
os.environ["EXAI_WS_TOKEN"] = ""
try:
    # If packaged, prefer relative import
    from .ws_exercise_all_tools import main  # type: ignore
except Exception:
    # Fallback: import by module name in same folder
    import importlib
    w = importlib.import_module("ws_exercise_all_tools")
    main = w.main

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

