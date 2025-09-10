"""
Lightweight JSONL observability helpers for EX MCP Server.

- record_token_usage: append token usage records to EX_METRICS_LOG_PATH
- record_file_count: append file count delta events to EX_METRICS_LOG_PATH
- record_error: append error events to EX_METRICS_LOG_PATH

Designed to be best-effort and non-intrusive. Failures are swallowed.
"""
from __future__ import annotations

import json
import os
import time
from typing import Optional


def _log_path() -> str:
    p = os.getenv("EX_METRICS_LOG_PATH", ".logs/metrics.jsonl").strip()
    # allow env to disable by setting empty
    return p


def _write_jsonl(obj: dict) -> None:
    path = _log_path()
    if not path:
        return
    try:
        base = os.path.dirname(path)
        if base and not os.path.exists(base):
            os.makedirs(base, exist_ok=True)
        obj.setdefault("t", time.time())
        line = json.dumps(obj, ensure_ascii=False)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # observability must never break flows
        pass


def record_token_usage(provider: str, model: str, input_tokens: int = 0, output_tokens: int = 0) -> None:
    try:
        _write_jsonl({
            "event": "token_usage",
            "provider": provider,
            "model": model,
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
        })
    except Exception:
        pass


def record_file_count(provider: str, delta: int) -> None:
    try:
        _write_jsonl({
            "event": "file_count_delta",
            "provider": provider,
            "delta": int(delta),
        })
    except Exception:
        pass


def record_error(provider: str, model: str, error_type: str, message: Optional[str] = None) -> None:
    try:
        _write_jsonl({
            "event": "provider_error",
            "provider": provider,
            "model": model,
            "error_type": str(error_type),
            "message": message or "",
        })
    except Exception:
        pass


def record_cache_hit(provider: str, sha: Optional[str] = None) -> None:
    try:
        obj = {"event": "file_cache", "action": "hit", "provider": provider}
        if sha:
            obj["sha"] = sha
        _write_jsonl(obj)
    except Exception:
        pass


def record_cache_miss(provider: str, sha: Optional[str] = None) -> None:
    try:
        obj = {"event": "file_cache", "action": "miss", "provider": provider}
        if sha:
            obj["sha"] = sha
        _write_jsonl(obj)
    except Exception:
        pass

