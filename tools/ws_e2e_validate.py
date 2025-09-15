import asyncio
import json
import os
import uuid
from pathlib import Path

import websockets

HOST = os.getenv("EXAI_WS_HOST", "127.0.0.1")
PORT = int(os.getenv("EXAI_WS_PORT", "8765"))
TOKEN = os.getenv("EXAI_WS_TOKEN", "")
ROOT = Path(__file__).resolve().parents[1]
FLAGS = str(ROOT / "docs" / "flags.md")

TOOLS = [
    ("analyze", {
        "step": "E2E validation - analyze flags.md",
        "step_number": 1,
        "total_steps": 1,
        "next_step_required": False,
        "findings": "Confirm router, chunked reader, proactive fallback, single-response.",
        "relevant_files": [FLAGS],
        "use_assistant_model": True,
        "temperature": 0,
        "thinking_mode": "minimal",
        "use_websearch": False,
        "analysis_type": "general",
        "output_format": "summary",
    }),
    ("codereview", {
        "step": "E2E validation - codereview flags.md",
        "step_number": 1,
        "total_steps": 1,
        "next_step_required": False,
        "findings": "Validate final-step embedding + fallback.",
        "relevant_files": [FLAGS],
        "use_assistant_model": True,
        "temperature": 0,
        "thinking_mode": "minimal",
        "use_websearch": False,
        "review_type": "full",
        "focus_on": "Final-step embedding and deferred response behavior",
        "severity_filter": "all",
    }),
    ("debug", {
        "step": "E2E validation - debug workflow",
        "step_number": 1,
        "total_steps": 1,
        "next_step_required": False,
        "findings": "No bug, validation run.",
        "relevant_files": [FLAGS],
        "use_assistant_model": True,
        "temperature": 0,
        "thinking_mode": "minimal",
        "use_websearch": False,
    }),
]

async def call_tool(ws, name, args):
    rid = uuid.uuid4().hex
    await ws.send(json.dumps({"op": "call_tool", "request_id": rid, "name": name, "arguments": args}))
    while True:
        msg = json.loads(await ws.recv())
        if msg.get("op") == "progress":
            # print("[progress]", msg.get("message"))
            continue
        if msg.get("op") == "call_tool_res" and msg.get("request_id") == rid:
            return msg

async def main():
    uri = f"ws://{HOST}:{PORT}"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"op": "hello", "session_id": f"e2e-{uuid.uuid4().hex[:6]}", "token": TOKEN}))
        ack = json.loads(await ws.recv())
        if not ack.get("ok"):
            raise SystemExit(f"Auth failed: {ack}")
        print("[E2E] Connected")
        for name, args in TOOLS:
            print(f"[E2E] Calling {name} ...")
            res = await call_tool(ws, name, args)
            if res.get("error"):
                print(f"[E2E] {name} error: {res['error']}")
            else:
                outs = res.get("outputs", [])
                text = outs[0].get("text") if outs else None
                print(f"[E2E] {name} outputs: {bool(text)}, length={len(text or '')}")
                if text:
                    print(text[:2400])

if __name__ == "__main__":
    asyncio.run(main())

