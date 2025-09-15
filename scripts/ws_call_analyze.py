#!/usr/bin/env python
"""
Call the MCP 'analyze' tool over the running WS daemon to validate:
- SECURE_INPUTS_ENFORCED relative-path normalization (relevant_files)
- Non-provider Phase 1 flow (next_step_required=False) should not require model calls
"""
import asyncio
import json
import os
from pathlib import Path
import uuid

import websockets

HOST = os.getenv("EXAI_WS_HOST", "127.0.0.1")
PORT = int(os.getenv("EXAI_WS_PORT", "8765"))
TOKEN = os.getenv("EXAI_WS_TOKEN", "")
REPO_ROOT = Path(__file__).resolve().parents[1]

async def main() -> int:
    uri = f"ws://{HOST}:{PORT}"
    sid = f"ws-analyze-{uuid.uuid4().hex[:6]}"
    async with websockets.connect(uri, max_size=20 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"op": "hello", "session_id": sid, "token": TOKEN}))
        ack = json.loads(await ws.recv())
        if not ack.get("ok"):
            print("Auth failed:", ack)
            return 2

        # Prepare analyze Phase 1 (no model call) with relative file path
        req_id = uuid.uuid4().hex
        args = {
            "step": "Kickoff",
            "step_number": 1,
            "total_steps": 1,
            "next_step_required": True,  # keep Phase 1 local (no expert analysis)
            "use_assistant_model": False,  # explicit: do NOT call provider
            "findings": "ws analyze e2e",
            "analysis_type": "general",
            "output_format": "summary",
            "relevant_files": ["server.py"],  # relative on purpose
        }
        await ws.send(json.dumps({
            "op": "call_tool",
            "request_id": req_id,
            "name": "analyze",
            "arguments": args,
        }))

        # Await response
        while True:
            raw = await ws.recv()
            msg = json.loads(raw)
            if msg.get("op") == "call_tool_res" and msg.get("request_id") == req_id:
                if msg.get("error"):
                    print("Error:", msg["error"])  # type: ignore[index]
                    return 1
                print(json.dumps(msg.get("outputs", []), ensure_ascii=False, indent=2))
                return 0

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

