import asyncio
import json
import os
import uuid
import websockets

HOST = os.getenv("EXAI_WS_HOST", "127.0.0.1")
PORT = int(os.getenv("EXAI_WS_PORT", "8765"))
TOKEN = os.getenv("EXAI_WS_TOKEN", "")

async def main():
    uri = f"ws://{HOST}:{PORT}"
    async with websockets.connect(uri, ping_interval=60, ping_timeout=30, close_timeout=10) as ws:
        await ws.send(json.dumps({"op": "hello", "session_id": f"act-{uuid.uuid4().hex[:6]}", "token": TOKEN}))
        ack = json.loads(await ws.recv())
        if not ack.get("ok"):
            raise SystemExit(f"Auth failed: {ack}")
        rid = uuid.uuid4().hex
        args = {"lines": 20, "source": "auto"}
        await ws.send(json.dumps({"op": "call_tool", "request_id": rid, "name": "activity", "arguments": args}))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("op") == "call_tool_res" and msg.get("request_id") == rid:
                if msg.get("error"):
                    print("activity error:", msg.get("error"))
                else:
                    outs = msg.get("outputs") or []
                    text = outs[0].get("text", "") if outs and isinstance(outs[0], dict) else str(outs)
                    print("activity ok, preview:\n", text[:400])
                break

if __name__ == "__main__":
    asyncio.run(main())

