from __future__ import annotations

from typing import Dict, Set


class RBAC:
    def __init__(self, policy: Dict[str, Set[str]] | None = None) -> None:
        # policy: role -> allowed_tools set
        self.policy: Dict[str, Set[str]] = policy or {
            "admin": {"*"},
            "developer": {"analyze", "codereview", "testgen", "thinkdeep", "planner"},
            "viewer": {"thinkdeep", "planner"},
        }

    def can_execute(self, tool: str, role: str) -> bool:
        allowed = self.policy.get(role, set())
        return "*" in allowed or tool in allowed

