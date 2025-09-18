import asyncio
import json
import os
import uuid

import websockets

HOST = os.getenv("EXAI_WS_HOST", "127.0.0.1")
PORT = int(os.getenv("EXAI_WS_PORT", "8765"))
TOKEN = os.getenv("EXAI_WS_TOKEN", "")

async def wait_for_tool_result(ws, rid: str, tag: str, label: str = "call"):
    while True:
        msg = json.loads(await ws.recv())
        if msg.get("op") == "call_tool_res" and msg.get("request_id") == rid:
            if msg.get("error"):
                print(f"[{tag}] {label} error:", msg.get("error"))
            else:
                outs = msg.get("outputs") or []
                preview = outs[0].get("text")[:180] if outs and isinstance(outs[0], dict) else str(outs)[:180]
                print(f"[{tag}] {label} outputs (n={len(outs)}):", preview)
            break

async def run_client(tag: str = "A"):
    uri = f"ws://{HOST}:{PORT}"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"op": "hello", "session_id": f"test-{tag}-{uuid.uuid4().hex[:6]}", "token": TOKEN}))
        ack = json.loads(await ws.recv())
        if not ack.get("ok"):
            raise SystemExit(f"Auth failed: {ack}")
        await ws.send(json.dumps({"op": "list_tools"}))
        tools_msg = json.loads(await ws.recv())
        tools = tools_msg.get("tools", [])
        names = [t.get("name") for t in tools]
        print(f"[{tag}] tools count:", len(names))

        # 1) version
        if "version" in names:
            rid = uuid.uuid4().hex
            await ws.send(json.dumps({"op": "call_tool", "request_id": rid, "name": "version", "arguments": {}}))
            await wait_for_tool_result(ws, rid, tag, label="version")

        # 2) stream_demo fallback and streaming
        if "stream_demo" in names:
            # fallback (non-stream)
            rid = uuid.uuid4().hex
            await ws.send(json.dumps({
                "op": "call_tool", "request_id": rid, "name": "stream_demo",
                "arguments": {"prompt": "hello world", "provider": "zai", "stream": False}
            }))
            await wait_for_tool_result(ws, rid, tag, label="stream_demo_fallback")

            # streaming (first chunk)
            rid = uuid.uuid4().hex
            await ws.send(json.dumps({
                "op": "call_tool", "request_id": rid, "name": "stream_demo",
                "arguments": {"prompt": "streaming test", "provider": "moonshot", "stream": True}
            }))
            await wait_for_tool_result(ws, rid, tag, label="stream_demo_stream")

        # 3) thinkdeep with web cues to exercise Z.ai/Kimi path
        if "thinkdeep" in names:
            rid = uuid.uuid4().hex
            args = {
                "step": "Investigate current status and latest docs at https://example.com today",
                "step_number": 1,
                "total_steps": 1,
                "next_step_required": False,
                "findings": "Kickoff",
                "use_websearch": True,
                "model": "auto"
            }
            await ws.send(json.dumps({"op": "call_tool", "request_id": rid, "name": "thinkdeep", "arguments": args}))
            await wait_for_tool_result(ws, rid, tag, label="thinkdeep_webcue")

        # 4) long-context chat to exercise Moonshot route via token threshold
        if "chat" in names:
            long_text = ("L" * 210000)  # ~210k chars ~ >52k tokens (4 chars/token heuristic)
            rid = uuid.uuid4().hex
            args = {
                "prompt": "Please summarize this very long context: " + long_text,
                "model": "auto",
                "use_websearch": False
            }
            await ws.send(json.dumps({"op": "call_tool", "request_id": rid, "name": "chat", "arguments": args}))
            await wait_for_tool_result(ws, rid, tag, label="chat_longcontext")

async def _amain():
    await asyncio.gather(run_client("A"))

if __name__ == "__main__":
    asyncio.run(_amain())
