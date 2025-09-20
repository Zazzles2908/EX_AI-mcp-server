import types
import pytest

from src.router.service import RouterService, RouteDecision


class DummyProv:
    def __init__(self, name):
        self._name = name

    def get_provider_type(self):
        T = types.SimpleNamespace()
        T.name = self._name
        return T


def test_choose_model_explicit_available(monkeypatch):
    rs = RouterService()

    def _gp(model):
        if model == "my-explicit-model":
            return DummyProv("GLM")
        return None

    monkeypatch.setattr("src.providers.registry.ModelProviderRegistry.get_provider_for_model", _gp)

    dec: RouteDecision = rs.choose_model("my-explicit-model")
    assert dec.chosen == "my-explicit-model"
    assert dec.reason == "explicit"
    assert dec.provider == "GLM"


def test_choose_model_auto_preferred_fast(monkeypatch):
    rs = RouterService()

    fast = rs._fast_default

    def _gp(model):
        if model == fast:
            return DummyProv("GLM")
        return None

    monkeypatch.setattr("src.providers.registry.ModelProviderRegistry.get_provider_for_model", _gp)

    dec: RouteDecision = rs.choose_model(None)
    assert dec.chosen == fast
    assert dec.reason == "auto_preferred"


def test_choose_model_with_hint_long_context(monkeypatch):
    rs = RouterService()

    long_ = rs._long_default

    def _gp(model):
        if model in (long_,):
            return DummyProv("KIMI")
        return None

    monkeypatch.setattr("src.providers.registry.ModelProviderRegistry.get_provider_for_model", _gp)

    hint = {"platform": "moonshot", "task_type": "long_context_analysis"}
    dec: RouteDecision = rs.choose_model_with_hint(None, hint)
    assert dec.chosen == long_
    assert dec.reason in ("auto_hint_applied", "auto_preferred")

