from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class RecoveryPlan:
    rto_minutes: int = 30
    rpo_minutes: int = 5

    def simulate_restore(self, backup_available: bool, infra_ok: bool) -> Tuple[bool, str]:
        if not backup_available:
            return False, "No backup available"
        if not infra_ok:
            return False, "Infrastructure not healthy"
        return True, "Restore simulated successfully"

