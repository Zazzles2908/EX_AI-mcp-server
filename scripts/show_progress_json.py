# Back-compat shim: forwards to canonical subfolder
if __name__ == "__main__":
    import pathlib, runpy, sys
    target = pathlib.Path(__file__).parent / "diagnostics" / "show_progress_json.py"
    try:
        runpy.run_path(str(target), run_name="__main__")
    except SystemExit as e:
        raise
    except Exception as e:
        print(f"Shim failed to run target {target}: {e}")
        sys.exit(1)
    sys.exit(0)


#!/usr/bin/env python3
import os, sys, json, asyncio
from pathlib import Path

# Ensure project root on sys.path when running from scripts/
PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

os.environ.setdefault("STREAM_PROGRESS", "true")
os.environ.setdefault("AUGGIE_CLI", "true")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("LOG_FORMAT", "plain")

import server  # noqa: F401

async def main():
    from server import handle_call_tool
    args = {
        "step": "Emit progress demo",
        "step_number": 1,
        "total_steps": 1,
        "next_step_required": False,
        "findings": "demo"
    }
    res = await handle_call_tool("planner", args)
    for item in res:
        text = getattr(item, "text", str(item))
        try:
            j = json.loads(text)
            print(json.dumps(j, indent=2, ensure_ascii=False))
        except Exception:
            print(text)

if __name__ == "__main__":
    asyncio.run(main())

