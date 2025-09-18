from __future__ import annotations

import json
import os
from typing import Dict, Any

from audit.audit_logger import AuditLogger


class FileAuditLogger(AuditLogger):
    """Audit logger that writes JSONL entries to disk with simple rotation."""

    def __init__(self, path: str = "logs/mcp_audit.log", max_bytes: int = 1_000_000) -> None:
        super().__init__()
        self.path = path
        self.max_bytes = max_bytes
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def _rotate_if_needed(self) -> None:
        try:
            if os.path.exists(self.path) and os.path.getsize(self.path) > self.max_bytes:
                base, ext = os.path.splitext(self.path)
                rotated = f"{base}.1{ext or ''}"
                if os.path.exists(rotated):
                    os.remove(rotated)
                os.replace(self.path, rotated)
        except Exception:
            pass

    def log(self, user: str, tool: str, params: Dict[str, Any], success: bool) -> None:
        super().log(user, tool, params, success)
        self._rotate_if_needed()
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(self.records[-1]) + "\n")

