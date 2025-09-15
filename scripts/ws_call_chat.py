#!/usr/bin/env python
"""
Call the MCP 'chat' tool over the running WS daemon for an end-to-end check.
- Uses EXAI_WS_HOST/EXAI_WS_PORT from env (defaults 127.0.0.1:8765)
- Sends a simple prompt and a relative file path to verify SecureInputValidator normalization
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
    sid = f"ws-chat-{uuid.uuid4().hex[:6]}"
    async with websockets.connect(uri, max_size=20 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"op": "hello", "session_id": sid, "token": TOKEN}))
        ack = json.loads(await ws.recv())
        if not ack.get("ok"):
            print("Auth failed:", ack)
            return 2

        # Prepare call
        req_id = uuid.uuid4().hex
        args = {
            "prompt": "Router/Validator E2E check: Please echo the model you used and confirm path normalization for files.",
            # Intentionally pass a relative path to test normalization under SECURE_INPUTS_ENFORCED=true
            "files": ["server.py"],
            "use_websearch": False,
        }
        await ws.send(json.dumps({
            "op": "call_tool",
            "request_id": req_id,
            "name": "chat",
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

