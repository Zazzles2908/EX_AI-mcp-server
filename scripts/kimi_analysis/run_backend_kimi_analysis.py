# -*- coding: utf-8 -*-
"""
Backend MCP Runner for Kimi Analysis (WS JSON-RPC)

- Connects to EXAI-WS WebSocket using low-level JSON-RPC (hello/list_tools/call_tool)
- Executes a deterministic sequence derived from docs/augment_reports/augment_review_02/kimi_analysis/*
- Writes a timestamped run folder with raw frames, per-call inputs/outputs, and a concise markdown report
- Generates unpredictable prompts to simulate real usage

Note: Intentionally avoids high-level tool wrappers; uses the same protocol as validate_exai_ws_kimi_tools.py but
with clearer transition logging and a slimmer set of flows focused on Kimi/GLM coordination.
"""
from __future__ import annotations

import asyncio
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import logging, time

# Real-time console logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def _log_status(event: str, detail: dict[str, Any] | None = None) -> None:
    msg = {"event": event, **(detail or {})}
    try:
        print(f"[RUN] {event} :: {json.dumps(detail or {}, ensure_ascii=False)}", flush=True)
    except Exception:
        print(f"[RUN] {event}", flush=True)
    try:
        _append_jsonl({"type": "status", **msg})
    except Exception:
        pass


try:
    import websockets  # type: ignore
except Exception as e:
    raise SystemExit("The 'websockets' package is required. Please install it.") from e

ROOT = Path(os.getcwd())
RUNS_DIR = ROOT / "docs/augment_reports/augment_review_02/kimi_analysis/runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
RUN_DIR = RUNS_DIR / f"run_{TS}"
RUN_DIR.mkdir(parents=True, exist_ok=True)

HOST = os.getenv("EXAI_WS_HOST", "127.0.0.1")
PORT = int(os.getenv("EXAI_WS_PORT", "8765"))
TOKEN = os.getenv("EXAI_WS_TOKEN", "")

KIMI_MODEL = os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview")
GLM_FLASH = os.getenv("GLM_FLASH_MODEL", "glm-4.5-flash")
GLM_QUALITY = os.getenv("GLM_QUALITY_MODEL", "glm-4.5")

SUMMARY_MD = RUN_DIR / "summary.md"
SUMMARY_JSONL = RUN_DIR / "summary.jsonl"


def _w(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(obj: Dict[str, Any]) -> None:
    with SUMMARY_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _rand_prompt() -> str:
    bank = [
        "List three non-obvious risks in this repo and why they matter.",
        "Explain one surprising performance pitfall likely in this codebase.",
        "Propose a quick win refactor with a measurable impact.",
        "Summarize the architecture style used here in 4 bullets.",
        "What would you test first to validate provider wiring?",
    ]
    return random.choice(bank)


async def _ws_connect(uri: str):
    open_timeout = int(os.getenv("EXAI_WS_OPEN_TIMEOUT", "60"))
    ping_interval = int(os.getenv("EXAI_WS_PING_INTERVAL", "45"))
    ping_timeout = int(os.getenv("EXAI_WS_PING_TIMEOUT", "120"))
    close_timeout = int(os.getenv("EXAI_WS_CLOSE_TIMEOUT", "10"))
    return await websockets.connect(
        uri,
        open_timeout=open_timeout,
        ping_interval=ping_interval,
        ping_timeout=ping_timeout,
        close_timeout=close_timeout,
        max_queue=None,
    )


async def _recv_until(ws, request_id: str, *, display: str = "", base_timeout: int | None = None) -> Dict[str, Any]:
    """
    Receive frames until call_tool_res for request_id with progress logging and timeout.
    - Logs progress and ack frames in real-time
    - Uses adaptive timeout: resets on progress frames
    - Returns synthetic error on timeout to allow fallback
    """
    # Caps from env
    call_timeout = base_timeout or int(os.getenv("EXAI_WS_CALL_TIMEOUT", os.getenv("TOOL_EXEC_TIMEOUT_SEC", "240")))
    max_timeout = int(os.getenv("EXAI_WS_CALL_TIMEOUT_MAX", "480"))
    # Start timers
    start = time.time()
    last_activity = start
    elapsed = lambda: time.time() - start  # noqa: E731

    while True:
        # Remaining time budget since last activity
        remain = max(1.0, call_timeout - (time.time() - last_activity))
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remain)
        except asyncio.TimeoutError:
            # Timeout: emit synthetic error and bail
            detail = {"request_id": request_id, "display": display, "elapsed_sec": round(elapsed(), 2), "timeout_sec": call_timeout}
            _log_status("timeout", detail)
            (RUN_DIR / f"timeout_{display or request_id}.json").write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"op": "call_tool_res", "request_id": request_id, "error": f"timeout after {call_timeout}s", "outputs": []}

        msg = json.loads(raw)
        # Persist every frame for offline analysis
        (RUN_DIR / f"ws_frame_{msg.get('op','unknown')}_{msg.get('request_id','')}.json").write_text(
            json.dumps(msg, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        op = msg.get("op")
        rid = msg.get("request_id")
        if op in ("call_tool_ack", "progress"):
            last_activity = time.time()
            if op == "call_tool_ack":
                _log_status("ack", {"rid": rid, "tool": display})
            else:
                prog = msg.get("progress") or {}
                _log_status("progress", {"rid": rid, "tool": display, **({"stage": prog.get("stage")} if isinstance(prog, dict) else {})})
            # Gentle backoff: extend timeout once if we saw progress
            if call_timeout < max_timeout:
                call_timeout = min(max_timeout, call_timeout + 60)
        if op == "call_tool_res" and rid == request_id:
            return msg


async def _call(ws, name: str, args: Dict[str, Any], *, label: str | None = None, timeout_override: int | None = None) -> Dict[str, Any]:
    import uuid
    rid = uuid.uuid4().hex
    payload = {"op": "call_tool", "request_id": rid, "name": name, "arguments": args}
    (RUN_DIR / f"call_{name}_{rid}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    disp = label or name
    _log_status("start_tool", {"tool": disp, "rid": rid})
    t0 = time.time()
    await ws.send(json.dumps(payload))
    res = await _recv_until(ws, rid, display=disp, base_timeout=timeout_override)
    dur = round(time.time() - t0, 2)

    ok = res.get("error") is None and (not isinstance(res.get("outputs"), dict) or res.get("outputs", {}).get("status") != "cancelled")
    _append_jsonl({"tool": disp, "rid": rid, "ok": ok, "duration_sec": dur, "preview": str(res.get("outputs"))[:200]})
    if not ok:
        _log_status("tool_error", {"tool": disp, "rid": rid, "duration_sec": dur, "error": res.get("error") or res.get("outputs")})
    else:
        _log_status("tool_complete", {"tool": disp, "rid": rid, "duration_sec": dur})
    return res


async def run_once() -> None:
    # Candidate URIs
    uris = [f"ws://{HOST}:{PORT}", f"ws://{HOST}:{PORT}/ws"]

    _log_status("connect_attempt", {"uris": uris})
    ws = None
    last_err = None
    connected_uri = None
    for u in uris:
        try:
            ws = await _ws_connect(u)
            connected_uri = u
            _log_status("connected", {"uri": u})
            break
        except Exception as e:
            last_err = e
            _log_status("connect_error", {"uri": u, "error": str(e)})
            continue
    if ws is None:
        raise SystemExit(f"WS connect failed: {last_err}")

    async with ws:
        await ws.send(json.dumps({"op": "hello", "session_id": f"kimi-backend-{TS}", "token": TOKEN}))
        ack = json.loads(await ws.recv())
        _w(RUN_DIR / "hello_ack.json", ack)
        _log_status("hello_ack", {"ok": bool(ack.get("ok"))})
        if not ack.get("ok"):
            raise SystemExit(f"Auth failed: {ack}")
        await ws.send(json.dumps({"op": "list_tools"}))
        tools_msg = json.loads(await ws.recv())
        _w(RUN_DIR / "tools_list.json", tools_msg)
        names = {t.get("name"): t for t in tools_msg.get("tools", [])}
        _log_status("tools_list", {"count": len(names)})

        def _has(t: str) -> bool:
            return t in names

        # Stage 1: Kimi upload & multi-file chat
        FILE_A = ROOT / ".validation_tmp" / "sample_a.txt"
        FILE_B = ROOT / ".validation_tmp" / "sample_b.txt"
        FILE_A.parent.mkdir(exist_ok=True)
        FILE_A.write_text("A: backend MCP runner sample file\n", encoding="utf-8")
        FILE_B.write_text("B: backend MCP runner sample file\n", encoding="utf-8")

        if _has("kimi_upload_and_extract"):
            await _call(ws, "kimi_upload_and_extract", {"files": [str(FILE_A)], "purpose": "file-extract"}, label="kimi_upload_and_extract")
        if _has("kimi_multi_file_chat"):
            res = await _call(ws, "kimi_multi_file_chat", {
                "files": [str(FILE_A), str(FILE_B)],
                "prompt": _rand_prompt(),
                "model": KIMI_MODEL,
                "temperature": 0.4
            }, label="kimi_multi_file_chat")
            failed = (res.get("error") is not None) or (isinstance(res.get("outputs"), dict) and res.get("outputs", {}).get("status") == "cancelled")
            if failed and _has("glm_multi_file_chat"):
                _log_status("fallback_triggered", {"from": "kimi_multi_file_chat", "to": "glm_multi_file_chat"})
                (RUN_DIR / "fallback_mode.txt").write_text("Triggered due to kimi timeout/error", encoding="utf-8")
                await _call(ws, "glm_multi_file_chat", {
                    "files": [str(FILE_A), str(FILE_B)],
                    "prompt": "Fallback path: provide a concise synthesis of these two small files.",
                    "model": GLM_QUALITY,
                    "temperature": 0.4
                }, label="glm_multi_file_chat")

        # Stage 2: GLM chat with websearch (to exercise browsing path)
        if _has("chat"):
            await _call(ws, "chat", {
                "prompt": "Find a recent AI infra news item and give 2 bullets with a URL.",
                "model": GLM_QUALITY,
                "use_websearch": True
            })

        # Stage 3: Minimal analyze step to capture route diagnostics
        if _has("analyze"):
            await _call(ws, "analyze", {
                "step": "Collect route diagnostics snapshot",
                "step_number": 1,
                "total_steps": 1,
                "next_step_required": False,
                "findings": "Running backend MCP — snapshot",
                "output_format": "summary",
                "model": KIMI_MODEL
            })

        # Write a tiny markdown roll-up
        md = [
            f"# Backend MCP Run — {TS}",
            "", "Artifacts:",
            f"- hello_ack.json", f"- tools_list.json", f"- summary.jsonl",
        ]
        SUMMARY_MD.write_text("\n".join(md), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(run_once())

