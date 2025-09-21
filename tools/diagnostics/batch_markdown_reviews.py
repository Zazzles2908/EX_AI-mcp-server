import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import websockets

HOST = os.getenv("EXAI_WS_HOST", "127.0.0.1")
PORT = int(os.getenv("EXAI_WS_PORT", "8765"))
TOKEN = os.getenv("EXAI_WS_TOKEN", "")

PROMPT = "Summarize this file in 5 bullets; list structural inconsistencies; propose fixes and a short actionable checklist."
FILES = [
    r"c:\\Project\\EX-AI-MCP-Server\\docs\\augment_reports\\architecture\\tools_inventory_current_2025-09-20.md",
    r"c:\\Project\\EX-AI-MCP-Server\\docs\\augment_reports\\architecture\\tools_reorg_proposal_2025-09-20.md",
    r"c:\\Project\\EX-AI-MCP-Server\\docs\\augment_reports\\architecture\\universal_ui_summary_2025-09-20.md",
    r"c:\\Project\\EX-AI-MCP-Server\\docs\\augment_reports\\architecture\\server_deep_dive_2025-09-20.md",
    r"c:\\Project\\EX-AI-MCP-Server\\docs\\augment_reports\\augment_review\\document_structure_current.md",
    r"c:\\Project\\EX-AI-MCP-Server\\docs\\augment_reports\\augment_review\\proposed_document_structure_2025-09-20.md",
]

OUT_PATH = Path("docs/augment_reports/augment_review/exai_ws_mcp_outputs_2025-09-21.md")

async def call_chat(ws, file_path: str) -> str:
    rid = uuid.uuid4().hex
    args = {
        "prompt": PROMPT,
        "files": [file_path],
        "model": "glm-4.5-flash",
        "temperature": 0.2,
        "thinking_mode": "minimal",
        "use_websearch": False,
    }
    await ws.send(json.dumps({"op": "call_tool", "request_id": rid, "name": "chat", "arguments": args}))
    # Wait for result
    while True:
        msg = json.loads(await ws.recv())
        if msg.get("op") == "call_tool_res" and msg.get("request_id") == rid:
            if msg.get("error"):
                return f"ERROR: {msg.get('error')}"
            outs = msg.get("outputs") or []
            # Extract text from outputs
            texts = []
            for o in outs:
                if isinstance(o, dict) and o.get("type") == "text":
                    texts.append(o.get("text", ""))
                else:
                    texts.append(str(o))
            return "\n".join(texts).strip()

async def main():
    uri = f"ws://{HOST}:{PORT}"
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with websockets.connect(uri, ping_interval=60, ping_timeout=30, close_timeout=10) as ws:
        await ws.send(json.dumps({"op": "hello", "session_id": f"batch-{uuid.uuid4().hex[:6]}", "token": TOKEN}))
        ack = json.loads(await ws.recv())
        if not ack.get("ok"):
            raise SystemExit(f"Auth failed: {ack}")
        # Ensure chat tool is available
        await ws.send(json.dumps({"op": "list_tools"}))
        tools_msg = json.loads(await ws.recv())
        names = [t.get("name") for t in tools_msg.get("tools", [])]
        if "chat" not in names:
            raise SystemExit("chat tool not available")

        lines = []
        lines.append(f"# EXAI-WS MCP Chat Outputs — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append(f"Prompt: {PROMPT}")
        lines.append("")
        for fp in FILES:
            lines.append(f"## File: {fp}")
            res = await call_chat(ws, fp)
            # Raw block
            lines.append("")
            lines.append("```md")
            lines.append(res)
            lines.append("```")
            lines.append("")
        OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
        print(f"Wrote outputs to: {OUT_PATH}")

if __name__ == "__main__":
    asyncio.run(main())

