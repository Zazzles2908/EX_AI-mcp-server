"""Tool call event and citation recording utilities.

Provides normalized event structures for provider-native tool calls (e.g., web_search)
so that UI and logs can display consistent information across providers.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import json
import os
import re
import time


def _redact_query(query: str) -> str:
    # Basic redaction: truncate and remove obvious tokens; configurable in future
    if not query:
        return query
    q = query.strip()
    if len(q) > 256:
        q = q[:256] + "..."
    return q


def _redact_url(url: str) -> str:
    try:
        # Remove query params for privacy
        return re.sub(r"\?.*$", "", url)
    except Exception:
        return url


@dataclass
class Citation:
    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None
    rank: Optional[int] = None
    source_provider: Optional[str] = None
    tool_call_id: Optional[str] = None

    def sanitized(self) -> Dict[str, Any]:
        data = asdict(self)
        data["url"] = _redact_url(self.url)
        return data


@dataclass
class ToolCallEvent:
    provider: str
    tool_name: str
    args: Dict[str, Any] = field(default_factory=dict)
    start_ts: float = field(default_factory=time.time)
    end_ts: Optional[float] = None
    latency_ms: Optional[float] = None
    citations: List[Citation] = field(default_factory=list)
    ok: Optional[bool] = None
    error: Optional[str] = None

    def end(self, ok: bool = True, error: Optional[str] = None):
        self.end_ts = time.time()
        self.latency_ms = (self.end_ts - self.start_ts) * 1000.0
        self.ok = ok
        self.error = error

    def sanitized(self) -> Dict[str, Any]:
        redaction = os.getenv("EX_TOOLCALL_REDACTION", "true").lower() == "true"
        d = asdict(self)
        if redaction:
            # sanitize args values that may contain queries/URLs
            if "query" in d.get("args", {}):
                d["args"]["query"] = _redact_query(str(d["args"]["query"]))
            # sanitize any url fields inside args
            for k, v in list(d.get("args", {}).items()):
                if isinstance(v, str) and v.startswith("http"):
                    d["args"][k] = _redact_url(v)
        d["citations"] = [c.sanitized() for c in self.citations]
        return d


class ToolEventSink:
    def __init__(self):
        # Expand env vars and ~, and normalize to absolute path
        p = os.getenv("EX_TOOLCALL_LOG_PATH", "").strip()
        if p:
            try:
                from os.path import expanduser, expandvars, abspath
                p = abspath(expanduser(expandvars(p)))
            except Exception:
                pass
        self._path = p
        self._log_enabled = bool(self._path)

    def record(self, event: ToolCallEvent) -> None:
        # Optional JSONL logging of sanitized events
        if not self._log_enabled:
            return
        try:
            # Ensure directory exists to avoid silent failures
            try:
                base_dir = os.path.dirname(self._path)
                if base_dir and not os.path.exists(base_dir):
                    os.makedirs(base_dir, exist_ok=True)
            except Exception:
                pass
            line = json.dumps(event.sanitized(), ensure_ascii=False)
            # Respect EX_TOOLCALL_LOG_LEVEL: debug/info/warn/error to gate writes
            level = os.getenv("EX_TOOLCALL_LOG_LEVEL", "info").strip().lower()
            if level in ("debug", "info"):
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
        except Exception:
            # Fail silently – observability shouldn't break user flows
            pass

