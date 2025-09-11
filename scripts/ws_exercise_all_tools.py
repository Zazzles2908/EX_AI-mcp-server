#!/usr/bin/env python
"""
Exercise all EX AI MCP tools via the running WS daemon.
- Connects to ws://EXAI_WS_HOST:EXAI_WS_PORT (defaults 127.0.0.1:8765)
- Lists tools and calls each with safe, minimal arguments
- Skips tools that likely require external provider API keys unless ALLOW_PROVIDER_TESTS=1
- Prints a summary at the end; exits 0 if most tools succeeded, 1 otherwise
"""
import asyncio
import json
import os
import random
import sys
import time
import uuid
from pathlib import Path

import websockets

HOST = os.getenv("EXAI_WS_HOST", "127.0.0.1")
PORT = int(os.getenv("EXAI_WS_PORT", "8765"))
TOKEN = os.getenv("EXAI_WS_TOKEN", "")
ALLOW_PROVIDER = os.getenv("ALLOW_PROVIDER_TESTS", "0") in ("1", "true", "TRUE")
REPO_ROOT = Path(__file__).resolve().parents[1]

SKIP_TOOLS = set()
# Skip provider-dependent tools unless user allows
if not ALLOW_PROVIDER:
    SKIP_TOOLS |= {"chat", "kimi_chat_with_tools", "kimi_upload_and_extract", "consensus"}


async def call_tool(ws, name: str, args: dict, timeout: float = 30.0) -> tuple[bool, str]:
    req_id = uuid.uuid4().hex
    await ws.send(json.dumps({"op": "call_tool", "request_id": req_id, "name": name, "arguments": args}))
    t0 = time.time()
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        msg = json.loads(raw)
        if msg.get("op") == "call_tool_res" and msg.get("request_id") == req_id:
            if msg.get("error"):
                return False, str(msg.get("error"))
            return True, json.dumps(msg.get("outputs", []))
        # Ignore other messages (e.g., logs)
        if (time.time() - t0) > timeout:
            return False, "timeout waiting for call_tool_res"


def default_args_for(tool: str) -> dict:
    # Minimal safe argument sets per tool
    if tool == "activity":
        return {"lines": 50, "filter": "TOOL_CALL|TOOL_COMPLETED"}
    if tool == "analyze":
        return {
            "step": "Kickoff",
            "step_number": 1,
            "total_steps": 1,
            "next_step_required": False,
            "findings": "ws exercise",
            "analysis_type": "general",
            "output_format": "summary",
        }
    if tool == "challenge":
        return {"prompt": "This is a drill."}
    if tool == "codereview":
        return {
            "step": "Kickoff",
            "step_number": 1,
            "total_steps": 1,
            "next_step_required": False,
            "findings": "ws exercise",
            "relevant_files": [str(REPO_ROOT / "server.py")],
            "review_type": "quick",
            "severity_filter": "low",
        }
    if tool == "debug":
        return {
            "step": "Investigate",
            "step_number": 1,
            "total_steps": 1,
            "next_step_required": False,
            "findings": "ws exercise",
            "confidence": "low",
        }
    if tool == "docgen":
        return {
            "step": "Kickoff",
            "step_number": 1,
            "total_steps": 1,
            "next_step_required": False,
            "findings": "ws exercise",
            "document_complexity": False,
            "document_flow": False,
            "update_existing": False,
            "comments_on_complex_logic": False,
            "num_files_documented": 0,
            "total_files_to_document": 0,
        }
    if tool == "health":
        return {"tail_lines": 50}
    if tool == "listmodels":
        return {}
    if tool == "planner":
        return {
            "step": "Outline goals",
            "step_number": 1,
            "total_steps": 1,
            "next_step_required": False,
        }
    if tool == "precommit":
        return {
            "step": "Kickoff",
            "step_number": 1,
            "total_steps": 1,
            "next_step_required": False,
            "findings": "ws exercise",
            "path": str(REPO_ROOT),
            "include_staged": False,
            "include_unstaged": False,
            "severity_filter": "low",
        }
    if tool == "provider_capabilities":
        return {"include_tools": True, "show_advanced": False}
    if tool == "refactor":
        return {
            "step": "Kickoff",
            "step_number": 1,
            "total_steps": 1,
            "next_step_required": False,
            "findings": "ws exercise",
            "refactor_type": "codesmells",
            "confidence": "incomplete",
        }
    if tool == "secaudit":
        return {
            "step": "Kickoff",
            "step_number": 1,
            "total_steps": 1,
            "next_step_required": False,
            "findings": "ws exercise",
            "relevant_files": [str(REPO_ROOT / "server.py")],
            "security_scope": "API",
            "threat_level": "low",
            "audit_focus": "owasp",
            "severity_filter": "low",
        }
    if tool == "testgen":
        return {
            "step": "Kickoff",
            "step_number": 1,
            "total_steps": 1,
            "next_step_required": False,
            "findings": "ws exercise",
            "confidence": "low",
        }
    if tool == "thinkdeep":
        return {
            "step": "Kickoff",
            "step_number": 1,
            "total_steps": 1,
            "next_step_required": False,
            "findings": "ws exercise",
            "confidence": "low",
        }
    if tool == "tracer":
        return {
            "step": "Kickoff",
            "step_number": 1,
            "total_steps": 1,
            "next_step_required": False,
            "findings": "ws exercise",
            "trace_mode": "ask",
            "target_description": "Trace server startup entrypoints",
        }
    if tool == "version":
        return {}
    # Default: empty
    return {}


async def main() -> int:
    uri = f"ws://{HOST}:{PORT}"
    sid = f"ws-exerciser-{uuid.uuid4().hex[:6]}-{random.randint(100,999)}"
    try:
        async with websockets.connect(uri, max_size=20 * 1024 * 1024) as ws:
            await ws.send(json.dumps({"op": "hello", "session_id": sid, "token": TOKEN}))
            ack = json.loads(await ws.recv())
            if not ack.get("ok"):
                print("Auth failed:", ack)
                return 2

            await ws.send(json.dumps({"op": "list_tools"}))
            tools_msg = json.loads(await ws.recv())
            tools = tools_msg.get("tools", [])
            names = [t.get("name") for t in tools]
            print("TOOLS:", ", ".join(sorted(names)))

            results = {}
            for name in names:
                if name in SKIP_TOOLS:
                    results[name] = (True, "skipped (provider)")
                    continue
                args = default_args_for(name)
                ok, info = await call_tool(ws, name, args)
                results[name] = (ok, info)
                print(f"{name}: {'OK' if ok else 'FAIL'}")

            # Summary
            oks = [n for n,(ok,_) in results.items() if ok]
            fails = {n:info for n,(ok,info) in results.items() if not ok}
            print("\nSummary:")
            print("  OK:", ", ".join(sorted(oks)))
            if fails:
                print("  FAIL:")
                for k,v in fails.items():
                    print("   -", k, "=>", (str(v)[:240]).replace("\n"," "))
            # Exit non-zero if any failures (excluding skipped)
            non_skipped = [n for n in names if n not in SKIP_TOOLS]
            ok_count = sum(1 for n in non_skipped if results.get(n,(False,''))[0])
            return 0 if ok_count == len(non_skipped) else 1
    except Exception as e:
        print("Connection failed:", e)
        return 3


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

