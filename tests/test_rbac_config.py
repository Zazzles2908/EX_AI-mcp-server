import json
import os
from security.rbac_config import load_policy


def test_rbac_config_from_env_json(monkeypatch):
    monkeypatch.delenv("RBAC_POLICY_FILE", raising=False)
    monkeypatch.setenv("RBAC_POLICY_JSON", json.dumps({"dev": ["analyze", "planner"]}))
    pol = load_policy()
    assert pol["dev"] == {"analyze", "planner"}

