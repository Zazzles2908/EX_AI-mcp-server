# Back-compat shim: forwards to canonical subfolder
if __name__ == "__main__":
    import pathlib, runpy, sys
    target = pathlib.Path(__file__).parent / "diagnostics" / "progress_test.py"
    try:
        runpy.run_path(str(target), run_name="__main__")
    except SystemExit as e:
        raise
    except Exception as e:
        print(f"Shim failed to run target {target}: {e}")
        sys.exit(1)
    sys.exit(0)


#!/usr/bin/env python3
"""
Quick progress visibility smoke test.
- Ensures server logging is configured by importing server
- Calls handle_call_tool for thinkdeep and analyze
- Prints results and relies on logging to emit [PROGRESS] breadcrumbs
"""
import os
import sys
import asyncio
from pathlib import Path

# Ensure project root on sys.path when running from scripts/
PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# Enable streaming-friendly env
os.environ.setdefault("STREAM_PROGRESS", "true")
os.environ.setdefault("AUGGIE_CLI", "true")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("LOG_FORMAT", "plain")
os.environ.setdefault("PYTHONPATH", str(PROJECT_DIR))

import server  # noqa: F401  # side effect: configures logging

async def run_thinkdeep():
    from server import handle_call_tool
    args = {
        "step": "Sanity test of progress emission in thinkdeep",
        "step_number": 1,
        "total_steps": 1,
        "next_step_required": False,
        "findings": "Initial step"
    }
    print("\n=== THINKDEEP CALL ===")
    res = await handle_call_tool("thinkdeep", args)
    print("RESULT:")
    for item in res:
        print(getattr(item, "text", str(item))[:500])

async def run_planner():
    from server import handle_call_tool
    args = {
        "step": "Create a 2-step plan to verify progress logging",
        "step_number": 1,
        "total_steps": 1,
        "next_step_required": False,
        "findings": "Testing progress helper"
    }
    print("\n=== PLANNER CALL ===")
    res = await handle_call_tool("planner", args)
    print("RESULT:")
    for item in res:
        print(getattr(item, "text", str(item))[:500])

async def run_analyze():
    from server import handle_call_tool
    # analyze step 1 requires non-empty relevant_files; use repo root
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    args = {
        "step": "Analyze project structure briefly",
        "step_number": 1,
        "total_steps": 1,
        "next_step_required": False,
        "findings": "Testing progress",
        "relevant_files": [repo_root],
        "files_checked": [repo_root]
    }
    print("\n=== ANALYZE CALL ===")
    res = await handle_call_tool("analyze", args)
    print("RESULT:")
    for item in res:
        print(getattr(item, "text", str(item))[:500])

async def main():
    await run_planner()
    await run_thinkdeep()
    await run_analyze()

if __name__ == "__main__":
    asyncio.run(main())

