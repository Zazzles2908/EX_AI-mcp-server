#!/usr/bin/env python
"""Copy of scripts/ws_status.py under scripts/ws."""
import json, os, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
HEALTH = ROOT / "logs" / "ws_daemon.health.json"
FRESH_SECS = float(os.getenv("WS_STATUS_FRESH_SECS", "20"))

def main() -> int:
    if not HEALTH.exists():
        print("ws_status: health file not found:", HEALTH); return 1
    try:
        data = json.loads(HEALTH.read_text(encoding="utf-8"))
    except Exception as e:
        print("ws_status: failed to read health file:", e); return 1
    now = time.time(); ts = float(data.get("t") or 0); age = now - ts if ts else 1e9
    host = data.get("host", os.getenv("EXAI_WS_HOST", "127.0.0.1"))
    port = data.get("port", int(os.getenv("EXAI_WS_PORT", "8765")))
    pid = data.get("pid"); sess = data.get("sessions"); inflight = data.get("global_inflight"); cap = data.get("global_capacity")
    state = "running" if age <= FRESH_SECS else f"stale ({int(age)}s old)"; pid_txt = str(pid) if pid is not None else "unknown"
    print(f"ws_status: {state} | ws://{host}:{port} | pid={pid_txt} | sessions={sess} inflight={inflight}/{cap}")
    return 0 if age <= FRESH_SECS else 1

if __name__ == "__main__":
    sys.exit(main())

