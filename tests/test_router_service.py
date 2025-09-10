import os
import json
from pathlib import Path

import pytest

# Ensure project root on sys.path
import sys
PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from src.router.service import RouterService
from src.providers.registry import ModelProviderRegistry as R


@pytest.mark.parametrize("requested,expect_auto", [
    ("auto", True),
    ("glm-4.5-flash", False),
])
def test_choose_model_prefer_explicit_or_fast(requested, expect_auto):
    rs = RouterService()
    dec = rs.choose_model(requested)
    assert dec.chosen
    if expect_auto:
        # auto should not return literal 'auto'
        assert dec.chosen.lower() != "auto"
    else:
        assert dec.chosen == requested


def test_preflight_does_not_raise(monkeypatch):
    rs = RouterService()
    # Force skip trivial chat if env disables
    monkeypatch.setenv("ROUTER_PREFLIGHT_CHAT", "false")
    rs.preflight()  # should not raise


def test_available_models_api():
    # ensure registry can enumerate models without raising
    models = R.get_available_models(respect_restrictions=True)
    assert isinstance(models, dict)

