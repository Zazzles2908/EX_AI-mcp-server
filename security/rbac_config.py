from __future__ import annotations

import json
import os
from typing import Dict, Set


def load_policy() -> Dict[str, Set[str]]:
    """Load RBAC policy from env file path or inline JSON.

    RBAC_POLICY_FILE: path to JSON file {role: [tools]}
    RBAC_POLICY_JSON: inline JSON string {role: [tools]}
    """
    path = os.getenv("RBAC_POLICY_FILE")
    text = os.getenv("RBAC_POLICY_JSON")
    data = None
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    elif text:
        data = json.loads(text)
    if not data:
        return {}
    return {k: set(v or []) for k, v in data.items()}

