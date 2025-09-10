import asyncio
import json
import os
import uuid

import websockets

HOST = os.getenv("EXAI_WS_HOST", "127.0.0.1")
PORT = int(os.getenv("EXAI_WS_PORT", "8765"))
TOKEN = os.getenv("EXAI_WS_TOKEN", "")

async def run_client(tag: str = "A"):
    uri = f"ws://{HOST}:{PORT}"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"op": "hello", "session_id": f"test-{tag}-{uuid.uuid4().hex[:6]}", "token": TOKEN}))
        ack = json.loads(await ws.recv())
        if not ack.get("ok"):
            raise SystemExit(f"Auth failed: {ack}")
        await ws.send(json.dumps({"op": "list_tools"}))
        tools_msg = json.loads(await ws.recv())
        print(f"[{tag}] tools count:", len(tools_msg.get("tools", [])))
        # Try version tool if available
        names = [t.get("name") for t in tools_msg.get("tools", [])]
        if "version" in names:
            rid = uuid.uuid4().hex
            await ws.send(json.dumps({"op": "call_tool", "request_id": rid, "name": "version", "arguments": {}}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("op") == "call_tool_res" and msg.get("request_id") == rid:
                    if msg.get("error"):
                        print(f"[{tag}] version error:", msg.get("error"))
                    else:
                        outs = msg.get("outputs")
                        print(f"[{tag}] version outputs (n={len(outs)}):", outs[0].get("text")[:120] if outs else "<none>")
                    break

async def _amain():
    await asyncio.gather(run_client("A"), run_client("B"))

if __name__ == "__main__":
    asyncio.run(_amain())

