from __future__ import annotations

import time
from typing import Dict, Any, List


class AuditLogger:
    def __init__(self) -> None:
        self.records: List[Dict[str, Any]] = []

    def log(self, user: str, tool: str, params: Dict[str, Any], success: bool) -> None:
        self.records.append(
            {
                "ts": time.time(),
                "user": user,
                "tool": tool,
                "success": success,
                "params": dict(params or {}),
            }
        )

