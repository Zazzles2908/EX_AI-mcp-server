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

