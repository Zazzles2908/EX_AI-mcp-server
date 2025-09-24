"""
Centralized logging configuration for EX-AI MCP Server.
This module is additive and not wired until imported by server.py.
"""
from __future__ import annotations
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional


class _LocalTimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        import time
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            t = time.strftime("%Y-%m-%d %H:%M:%S", ct)
            s = f"{t},{record.msecs:03.0f}"
        return s


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 20 * 1024 * 1024,  # 20MB
    backup_count: int = 5,
    json_format: bool = False,
) -> None:
    """Setup centralized logging with formatters and handlers.

    This mirrors current behavior (stderr + rotating file) but is centralized.
    """
    level = getattr(logging, (log_level or "INFO").upper(), logging.INFO)

    class _JsonLineFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            import json as _json
            payload = {
                "ts": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
            }
            if record.exc_info:
                payload["exc"] = self.formatException(record.exc_info)
            return _json.dumps(payload, ensure_ascii=False)

    # Clear existing handlers
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    # Console (stderr to match current server behavior)
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(_JsonLineFormatter() if json_format else _LocalTimeFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    root.addHandler(console)

    # Optional rotating file
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(_LocalTimeFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        root.addHandler(fh)

    root.setLevel(level)

    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("mcp_activity").setLevel(logging.INFO)

