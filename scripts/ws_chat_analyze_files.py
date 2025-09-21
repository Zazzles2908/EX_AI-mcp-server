#!/usr/bin/env python
"""
Call the EXAI-WS MCP "chat" tool for one or more markdown files using a fixed instruction prompt,
collect the visible model outputs (excluding Activity/Progress prefaces), and write a combined
Markdown report to a target path.

Usage:
  python scripts/ws_chat_analyze_files.py <output_markdown_path> <file1> <file2> ...

Environment:
  EXAI_WS_HOST, EXAI_WS_PORT, EXAI_WS_TOKEN (optional)
  DEFAULT_MODEL (optional, default: glm-4.5-flash)

This script connects directly to the running WS daemon.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, List, Tuple

import websockets  # type: ignore

HOST = os.getenv("EXAI_WS_HOST", "127.0.0.1")
PORT = int(os.getenv("EXAI_WS_PORT", "8765"))
TOKEN = os.getenv("EXAI_WS_TOKEN", "")
MODEL = os.getenv("DEFAULT_MODEL", "glm-4.5-flash")

INSTRUCTION = (
    "Summarize this file in 5 bullets; list structural inconsistencies; "
    "propose 3 actionable fixes with rationale and expected impact; flag any broken Mermaid; "
    "extract a verification checklist (5 items). Keep it concise."
)


def _extract_texts_and_content(outputs: Any) -> Tuple[List[str], str]:
    """Collect text blocks and try to extract ToolOutput.content if present."""
    texts: List[str] = []
    content_field: str = ""

    def maybe_parse_tooloutput(s: str) -> None:
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
                maybe_parse_tooloutput(s)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for it in x:
                walk(it)

    walk(outputs)
    return texts, content_field


def _strip_activity_and_progress(s: str) -> str:
    # Remove leading Activity/Progress summaries if present
    lines = s.splitlines()
    out: List[str] = []
    skipping = True
    i = 0
    while i < len(lines):
        line = lines[i]
        if skipping:
            if line.startswith("Activity:"):
                i += 1
                continue
            if line.strip().startswith("=== PROGRESS ==="):
                # Skip until end progress block
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("=== END PROGRESS ==="):
                    i += 1
                i += 1
                continue
            if line.strip().startswith("=== MCP CALL SUMMARY ==="):
                # Skip summary block until END SUMMARY
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("=== END SUMMARY ==="):
                    i += 1
                i += 1
                continue
            # First non-activity/progress/summary line switches skipping off
            skipping = False
        else:
            out.append(line)
            i += 1
            continue
        # After skipping one of the sections, loop without increment to reevaluate current position
    # If nothing collected (e.g., content started immediately), fallback to original
    body = "\n".join(out).strip()
    return body if body else s.strip()


async def _ws_call_chat(ws, prompt: str, model: str, timeout: float = 180.0) -> Any:
    req_id = uuid.uuid4().hex
    args = {"prompt": prompt, "model": model, "temperature": 0.0}
    await ws.send(json.dumps({"op": "call_tool", "request_id": req_id, "name": "chat", "arguments": args}))
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        msg = json.loads(raw)
        if msg.get("op") == "call_tool_res" and msg.get("request_id") == req_id:
            if msg.get("error"):
                raise RuntimeError(str(msg.get("error")))
            return msg.get("outputs", [])


async def analyze_files(output_path: Path, files: List[Path], model: str) -> int:
    sections: List[str] = []
    header = [
        f"# EXAI-WS MCP Chat Outputs — {Path(output_path).name}",
        "",
        f"Prompt: {INSTRUCTION}",
        "",
    ]
    sections.extend(header)

    for f in files:
        uri = f"ws://{HOST}:{PORT}"
        async with websockets.connect(
            uri,
            max_size=20 * 1024 * 1024,
            ping_interval=30,
            ping_timeout=30,
            close_timeout=5,
        ) as ws:
            # Separate connection per file to avoid long-lived keepalive timeouts
            await ws.send(json.dumps({"op": "hello", "session_id": f"ws-file-{uuid.uuid4().hex[:6]}", "token": TOKEN}))
            ack = json.loads(await ws.recv())
            if not ack.get("ok"):
                print("[WS] Auth failed:", ack)
                return 2

            text = f.read_text(encoding="utf-8", errors="ignore")
            prompt = (
                f"{INSTRUCTION}\n\nFile: {f.resolve()}\n\n<BEGIN FILE>\n{text}\n<END FILE>\n"
            )
            outputs = await _ws_call_chat(ws, prompt, model, timeout=1200.0)
            texts, content_field = _extract_texts_and_content(outputs)
            visible = content_field.strip() if content_field.strip() else "\n".join(t for t in texts if t).strip()
            visible = _strip_activity_and_progress(visible)

            sections.append(f"## File: {f.resolve()}\n")
            sections.append("```md")
            sections.append(visible)
            sections.append("````")
            sections[-1] = "```"
            sections.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(sections), encoding="utf-8")
    print(f"WROTE: {output_path}")
    return 0


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python scripts/ws_chat_analyze_files.py <output_markdown_path> <file1> <file2> ...")
        return 64
    out = Path(sys.argv[1]).resolve()
    files = [Path(p).resolve() for p in sys.argv[2:]]
    for p in files:
        if not p.exists():
            print(f"Missing file: {p}")
            return 66
    return asyncio.run(analyze_files(out, files, MODEL))


if __name__ == "__main__":
    raise SystemExit(main())

