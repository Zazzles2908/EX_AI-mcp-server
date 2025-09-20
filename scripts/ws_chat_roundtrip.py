#!/usr/bin/env python
"""
Call the EXAI-WS MCP "chat" tool twice (GLM and KIMI) and print returned text.
- Uses WS host/port/token from environment (EXAI_WS_HOST/EXAI_WS_PORT/EXAI_WS_TOKEN)
- Sends minimal arguments: {"prompt": <prompt>, "model": <model>, "temperature": 0.0}
- Prints the raw outputs JSON and a best-effort concatenated text for each call
- Additionally, if a ToolOutput JSON is detected (status=continuation_available/success), extract its 'content' field.
Exit codes: 0 on success (both calls attempted regardless of first result)
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from typing import Any, List, Tuple

import websockets  # same dep used by ws_exercise_all_tools.py

HOST = os.getenv("EXAI_WS_HOST", "127.0.0.1")
PORT = int(os.getenv("EXAI_WS_PORT", "8765"))
TOKEN = os.getenv("EXAI_WS_TOKEN", "")

TESTS = [
    {"model": os.getenv("GLM_FAST_MODEL", "glm-4.5-flash"), "prompt": "Respond with exactly: OK (no preface, no quotes)"},
    {"model": os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview"), "prompt": "Respond with exactly: OK (no preface, no quotes)"},
]


def _extract_text(outputs: Any) -> Tuple[str, str]:
    """Best-effort: collect any 'text' fields and also parse ToolOutput JSON for 'content'.
    Returns (joined_texts, extracted_content_field).
    """
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


async def call_chat(ws, model: str, prompt: str, timeout: float = 120.0) -> tuple[bool, str, str, Any]:
    req_id = uuid.uuid4().hex
    args = {
        "prompt": prompt,
        "model": model,
        "temperature": 0.0,
    }
    await ws.send(json.dumps({"op": "call_tool", "request_id": req_id, "name": "chat", "arguments": args}))
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        msg = json.loads(raw)
        if msg.get("op") == "call_tool_res" and msg.get("request_id") == req_id:
            if msg.get("error"):
                return False, str(msg.get("error")), "", None
            outputs = msg.get("outputs", [])
            joined, content_field = _extract_text(outputs)
            return True, joined, content_field, outputs


async def main() -> int:
    uri = f"ws://{HOST}:{PORT}"
    try:
        async with websockets.connect(uri, max_size=20 * 1024 * 1024) as ws:
            await ws.send(json.dumps({"op": "hello", "session_id": f"ws-chat-{uuid.uuid4().hex[:6]}", "token": TOKEN}))
            ack = json.loads(await ws.recv())
            if not ack.get("ok"):
                print("[WS] Auth failed:", ack)
                return 2

            exit_code = 0
            for t in TESTS:
                model = t["model"]
                prompt = t["prompt"]
                try:
                    ok, joined, content_field, outputs = await call_chat(ws, model, prompt)
                    print(f"\n=== chat call ({model}) ===")
                    print("Prompt:", prompt)
                    print("OK:", ok)
                    if outputs is not None:
                        print("Raw outputs:", json.dumps(outputs, ensure_ascii=False)[:1600])
                    print("Text (joined):", (joined or "<empty>")[:600])
                    if content_field:
                        print("Content field:", content_field[:600])
                    else:
                        print("Content field: <empty>")
                    if not ok:
                        exit_code = 1
                except Exception as e:
                    print(f"\n=== chat call ({model}) ===")
                    print("Prompt:", prompt)
                    print("Exception:", repr(e))
                    exit_code = 1
            return exit_code
    except Exception as e:
        print("Connection failed:", e)
        return 3


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

