# -*- coding: utf-8 -*-
"""
EXAI-WS MCP Validation Script (Kimi + GLM)

Purpose:
- Systematically exercise EXAI-WS MCP tool functions to validate Kimi platform capabilities and GLM coordination.
- Cover chat/analyze/thinkdeep workflows, continuation_id handling, Kimi file upload + multi-file chat, and optional CLI validations
  for embeddings and files cleanup.

Outputs:
- Creates a validation run folder under docs/augment_reports/augment_review_02/validation/runs/<timestamp>/
- Writes JSONL summary, per-call JSON outputs, and CLI stdout captures (for embeddings/cleanup)

Usage:
  python -X utf8 scripts/validate_exai_ws_kimi_tools.py [--fast]

Env:
- EXAI_WS_HOST, EXAI_WS_PORT, EXAI_WS_TOKEN
- KIMI_DEFAULT_MODEL, KIMI_FALLBACK_ORDER, GLM_* model vars (optional); KIMI_API_KEY for CLI extras
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Optional: auto-load .env for local runs
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

try:
    import websockets  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit("The 'websockets' package is required. Please install it in your environment.") from e

# Workspace root (repo root)
ROOT = Path(os.getcwd())
RUNS_DIR = ROOT / "docs/augment_reports/augment_review_02/validation/runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

HOST = os.getenv("EXAI_WS_HOST", "127.0.0.1")
PORT = int(os.getenv("EXAI_WS_PORT", "8765"))
TOKEN = os.getenv("EXAI_WS_TOKEN", "")

KIMI_MODEL_A = os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview")
KIMI_MODEL_B = os.getenv("KIMI_ALT_MODEL", "kimi-k2-0905-preview")
GLM_FLASH = os.getenv("GLM_FLASH_MODEL", "glm-4.5-flash")
GLM_QUALITY = os.getenv("GLM_QUALITY_MODEL", "glm-4.5")

from datetime import timezone as _TZ
TS = datetime.now(_TZ.utc).strftime("%Y%m%dT%H%M%SZ")
RUN_DIR = RUNS_DIR / f"run_{TS}"
RUN_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY_PATH = RUN_DIR / "summary.jsonl"

# Small temp files for upload/multi-file chat
TMP_DIR = ROOT / ".validation_tmp"
TMP_DIR.mkdir(exist_ok=True)
FILE_A = TMP_DIR / "sample_a.txt"
FILE_B = TMP_DIR / "sample_b.txt"
FILE_A.write_text("This is sample file A for Kimi file upload and extraction.\n", encoding="utf-8")
FILE_B.write_text("This is sample file B for Kimi multi-file chat validation.\n", encoding="utf-8")


def _write_json(obj: Any, path: Path) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_summary(line_obj: Dict[str, Any]) -> None:
    with SUMMARY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line_obj, ensure_ascii=False) + "\n")


async def _wait_for_tool_result(ws, rid: str, label: str) -> Dict[str, Any]:
    """Wait for the matching call_tool_res frame and normalize output."""
    while True:
        raw = await ws.recv()
        msg = json.loads(raw)
        if msg.get("op") == "call_tool_res" and msg.get("request_id") == rid:
            err = msg.get("error")
            outs = msg.get("outputs") or []
            # Persist full outputs
            _write_json(msg, RUN_DIR / f"tool_{label}_{rid}.json")
            return {"error": err, "outputs": outs}


async def _call_tool(ws, name: str, arguments: Dict[str, Any], label: str) -> Dict[str, Any]:
    rid = uuid.uuid4().hex
    await ws.send(json.dumps({"op": "call_tool", "request_id": rid, "name": name, "arguments": arguments}))
    res = await _wait_for_tool_result(ws, rid, label)
    ok = res.get("error") is None
    # Write summary row
    preview = None
    outs = res.get("outputs") or []
    if outs and isinstance(outs, list) and isinstance(outs[0], dict) and "text" in outs[0]:
        try:
            preview = str(outs[0]["text"])[:200]
        except Exception:
            preview = str(outs)[:200]
    _append_summary({"tool": name, "label": label, "ok": ok, "error": res.get("error"), "preview": preview})
    return res


async def validate_ws_tools(fast: bool = False) -> Dict[str, Any]:
    # Build candidate URIs (fallbacks for different server mounts)
    uris: list[str] = [
        f"ws://{HOST}:{PORT}",
        f"ws://{HOST}:{PORT}/ws",
    ]
    _remote = os.getenv("MCP_REMOTE_PORT", "")
    if _remote:
        try:
            uris.append(f"ws://{HOST}:{int(_remote)}")
        except Exception:
            pass

    totals = {"attempted": 0, "ok": 0, "failed": 0}

    # Harden WS keepalive behavior for EXAI-WS daemon
    # Resolve keepalive settings from env with sensible defaults
    _ping_interval = int(os.getenv("EXAI_WS_PING_INTERVAL", "45"))
    _ping_timeout = int(os.getenv("EXAI_WS_PING_TIMEOUT", "120"))
    _close_timeout = int(os.getenv("EXAI_WS_CLOSE_TIMEOUT", "10"))

    async def _connect_once(_uri: str):
        _open_timeout = int(os.getenv("EXAI_WS_OPEN_TIMEOUT", "60"))
        return await websockets.connect(
            _uri,
            open_timeout=_open_timeout,
            ping_interval=_ping_interval,
            ping_timeout=_ping_timeout,
            close_timeout=_close_timeout,
            max_queue=None,
        )

    ws = None
    last_err: Exception | None = None
    for _uri in uris:
        try:
            ws = await _connect_once(_uri)
            break
        except Exception as e:
            last_err = e
            # quick retry for this URI
            try:
                await asyncio.sleep(2.0)
                ws = await _connect_once(_uri)
                break
            except Exception as e2:
                last_err = e2
                continue
    if ws is None:
        raise SystemExit(f"WS connect failed for all URIs {uris}: {last_err}")

    async with ws:
        # Hello/auth
        await ws.send(json.dumps({"op": "hello", "session_id": f"val-{uuid.uuid4().hex[:6]}", "token": TOKEN}))
        ack = json.loads(await ws.recv())
        if not ack.get("ok"):
            raise SystemExit(f"Auth failed: {ack}")

        # Discover tools
        await ws.send(json.dumps({"op": "list_tools"}))
        tools_msg = json.loads(await ws.recv())
        tools = tools_msg.get("tools", [])
        names = {t.get("name"): t for t in tools}
        _write_json(tools_msg, RUN_DIR / "tools_list.json")

        async def try_call(name: str, args: Dict[str, Any], label: str):
            if name not in names:
                _append_summary({"tool": name, "label": label, "ok": False, "error": "not_exposed"})
                totals["attempted"] += 1
                totals["failed"] += 1
                return
            totals["attempted"] += 1
            res = await _call_tool(ws, name, args, label)
            if res.get("error") is None:
                totals["ok"] += 1
            else:
                totals["failed"] += 1

        # 1) chat: Kimi A, Kimi B, GLM flash + GLM web search (quality)
        await try_call("chat", {"prompt": "Say hi from Kimi A.", "model": KIMI_MODEL_A}, "chat_kimi_a")
        if not fast:
            await try_call("chat", {"prompt": "Say hi from Kimi B.", "model": KIMI_MODEL_B}, "chat_kimi_b")
        await try_call("chat", {"prompt": "Say hi from GLM flash.", "model": GLM_FLASH}, "chat_glm_flash")
        # Zhipu web search integration check: ask for 2 bullets with sources; server-side GLM web browsing should assist
        await try_call("chat", {
            "prompt": "Using web browsing, find today's top AI news and provide 2 concise bullets with source URLs.",
            "model": GLM_QUALITY,
            "use_websearch": True
        }, "chat_glm_websearch")

        # 2) thinkdeep (simple)
        await try_call("thinkdeep", {
            "step": "Quick web-backed check of current status (safe)",
            "step_number": 1,
            "total_steps": 1,
            "next_step_required": False,
            "findings": "Kickoff",
            "use_websearch": True,
            "model": "auto"
        }, "thinkdeep_web")

        # 3) analyze multi-step with continuation flow
        step1 = {
            "step": "Kickoff: inventory a couple files",
            "step_number": 1,
            "total_steps": 2,
            "next_step_required": True,
            "findings": "Investigating",
            "relevant_files": [str(ROOT / "tools/registry.py"), str(ROOT / "server.py")],
            "analysis_type": "general",
            "output_format": "summary",
            "model": KIMI_MODEL_A,
        }
        await try_call("analyze", step1, "analyze_step1")
        step2 = {
            "step": "Synthesize findings and risks",
            "step_number": 2,
            "total_steps": 2,
            "next_step_required": False,
            "findings": "Proceed to Kimi summary",
            "relevant_files": [],
            "output_format": "actionable",
            "model": KIMI_MODEL_A,
        }
        await try_call("analyze", step2, "analyze_step2")

        # 4) Kimi file upload + extract
        await try_call("kimi_upload_and_extract", {"files": [str(FILE_A)], "purpose": "file-extract"}, "kimi_upload_extract")

        # 5) Kimi multi-file chat
        await try_call("kimi_multi_file_chat", {
            "files": [str(FILE_A), str(FILE_B)],
            "prompt": "Briefly summarize the contents of both files.",
            "model": KIMI_MODEL_A,
            "temperature": 0.3
        }, "kimi_multi_file_chat")

        # 6) Optional GLM upload if exposed
        await try_call("glm_upload_file", {"file": str(FILE_A)}, "glm_upload_file")

        # 7) Planner quick smoke
        if not fast:
            await try_call("planner", {
                "step": "Outline a 2-step plan to validate tools",
                "step_number": 1,
                "total_steps": 2,
                "next_step_required": True
            }, "planner_step1")

        return totals


def _run_cli_tools() -> Dict[str, Any]:
    """Run optional CLI validations for embeddings and Kimi files cleanup."""
    results = {"embeddings": None, "cleanup": None}
    # Embeddings (if KIMI_EMBED_MODEL set)
    emb_model = os.getenv("KIMI_EMBED_MODEL", "")
    if emb_model:
        try:
            import subprocess
            p = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools/providers/kimi/kimi_embeddings.py"), "--text", "hello world"],
                               capture_output=True, text=True, cwd=str(ROOT))
            (RUN_DIR / "cli_embeddings_stdout.txt").write_text(p.stdout, encoding="utf-8")
            (RUN_DIR / "cli_embeddings_stderr.txt").write_text(p.stderr, encoding="utf-8")
            results["embeddings"] = {"rc": p.returncode, "stdout_len": len(p.stdout), "stderr_len": len(p.stderr)}
        except Exception as e:
            results["embeddings"] = {"error": str(e)}
    # Files cleanup (dry-run summary)
    try:
        import subprocess
        p = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools/providers/kimi/kimi_files_cleanup.py"), "--summary"],
                           capture_output=True, text=True, cwd=str(ROOT))
        (RUN_DIR / "cli_cleanup_stdout.txt").write_text(p.stdout, encoding="utf-8")
        (RUN_DIR / "cli_cleanup_stderr.txt").write_text(p.stderr, encoding="utf-8")
        results["cleanup"] = {"rc": p.returncode, "stdout_len": len(p.stdout), "stderr_len": len(p.stderr)}
    except Exception as e:
        results["cleanup"] = {"error": str(e)}
    # Log summary line
    _append_summary({"tool": "cli_extras", "label": "embeddings_cleanup", "ok": True, "preview": json.dumps(results)[:200]})
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="EXAI-WS MCP validation for Kimi/GLM")
    ap.add_argument("--fast", action="store_true", help="Run a reduced set of validations for speed")
    args = ap.parse_args()

    started = time.time()
    totals: Dict[str, Any] = {"attempted": 0, "ok": 0, "failed": 0}

    try:
        totals = asyncio.run(validate_ws_tools(fast=args.fast))
    except Exception as e:
        _append_summary({"tool": "__meta__", "label": "ws_error", "ok": False, "error": str(e)})
        print(f"WS validation error: {e}", file=sys.stderr)

    # Optional CLI validations
    extras = _run_cli_tools()

    dur = time.time() - started
    summary = {
        "attempted": totals.get("attempted", 0),
        "ok": totals.get("ok", 0),
        "failed": totals.get("failed", 0),
        "duration_sec": round(dur, 2),
        "run_dir": str(RUN_DIR),
        "cli": extras,
    }
    _write_json(summary, RUN_DIR / "final_summary.json")

    print(f"VALIDATION: PASS {summary['ok']}/{summary['attempted']} (failed={summary['failed']}) in {summary['duration_sec']}s")
    print(f"Artifacts: {summary['run_dir']}")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

