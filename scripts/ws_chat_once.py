# Back-compat shim: prefer canonical script in subfolder; this shim forwards and exits.
if __name__ == "__main__":
    import pathlib, runpy, sys
    target = pathlib.Path(__file__).parent / "ws" / "ws_chat_once.py"
    try:
        runpy.run_path(str(target), run_name="__main__")
    except SystemExit as e:
        raise
    except Exception as e:
        print(f"Shim failed to run target {target}: {e}")
        sys.exit(1)
    sys.exit(0)

#!/usr/bin/env python
"""
Call the EXAI-WS MCP "chat" tool once with (model, prompt) provided via CLI args and print returned text.
Usage:
  python scripts/ws_chat_once.py <model> <prompt>
Example:
  python scripts/ws_chat_once.py glm-4.5-flash "Say: hello"
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from typing import Any, List, Tuple

import websockets

HOST = os.getenv("EXAI_WS_HOST", "127.0.0.1")
PORT = int(os.getenv("EXAI_WS_PORT", "8765"))
TOKEN = os.getenv("EXAI_WS_TOKEN", "")


def _extract_text_and_content(outputs: Any) -> Tuple[str, str]:
    texts: List[str] = []
    content_field: str = ""

    def maybe_parse_tooloutput_text(s: str) -> None:
        nonlocal content_field
        try:
            obj = json.loads(s)
            if isinstance(obj, dict) and obj.get("status") in {"continuation_available", "success"}:
                c = obj.get("content")
                if isinstance(c, str) and not content_field:
                    content_field = c
        except Exception:
            pass

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            if x.get("type") == "text" and isinstance(x.get("text"), str):
                s = x["text"]
                texts.append(s)
                maybe_parse_tooloutput_text(s)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for it in x:
                walk(it)

    walk(outputs)
    return "\n".join(t for t in texts if t), content_field


async def call_chat(ws, model: str, prompt: str, timeout: float = 180.0):
    req_id = uuid.uuid4().hex
    args = {"prompt": prompt, "model": model, "temperature": 0.0}
    await ws.send(json.dumps({"op": "call_tool", "request_id": req_id, "name": "chat", "arguments": args}))
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        msg = json.loads(raw)
        if msg.get("op") == "call_tool_res" and msg.get("request_id") == req_id:
            if msg.get("error"):
                return False, str(msg.get("error")), None, None
            outputs = msg.get("outputs", [])
            joined, content_field = _extract_text_and_content(outputs)
            return True, joined, content_field, outputs


async def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python scripts/ws_chat_once.py <model> <prompt>")
        return 64
    model = sys.argv[1]
    prompt = " ".join(sys.argv[2:])

    uri = f"ws://{HOST}:{PORT}"
    try:
        async with websockets.connect(uri, max_size=20 * 1024 * 1024) as ws:
            await ws.send(json.dumps({"op": "hello", "session_id": f"ws-chat-{uuid.uuid4().hex[:6]}", "token": TOKEN}))
            ack = json.loads(await ws.recv())
            if not ack.get("ok"):
                print("[WS] Auth failed:", ack)
                return 2
            ok, joined, content_field, outputs = await call_chat(ws, model, prompt)
            print(f"Model: {model}")
            print(f"Prompt: {prompt}")
            print("OK:", ok)
            if outputs is not None:
                print("Raw outputs:", json.dumps(outputs, ensure_ascii=False)[:1600])
            print("Content field:")
            print((content_field or "<empty>")[:1200])
            return 0 if ok else 1
    except Exception as e:
        print("Connection failed:", e)
        return 3


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

