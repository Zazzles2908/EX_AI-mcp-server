from __future__ import annotations

import time
import types

from src.core.agentic.task_router import IntelligentTaskRouter, TaskType
from src.core.agentic.context_manager import AdvancedContextManager
from src.core.agentic.error_handler import ResilientErrorHandler, RetryPolicy
from src.core.validation.secure_input_validator import SecureInputValidator


def test_router_basic_routing():
    router = IntelligentTaskRouter()

    # Default classification: code generation
    req = {"messages": [{"role": "user", "content": "Write a function to add two numbers."}]}
    platform = router.select_platform(req)
    assert platform in {"moonshot", "zai", "hybrid"}

    # Multimodal routes to Z.ai
    req_multi = {"messages": [{"role": "user", "content": "Describe this image", "images": ["/tmp/x.png"]}]}
    assert router.classify(req_multi) == TaskType.MULTIMODAL_REASONING
    assert router.select_platform(req_multi) == "zai"

    # Long context routes to Moonshot
    long_text = "x" * (128_001 * 4)
    req_long = {"messages": [{"role": "user", "content": long_text}]}
    assert router.classify(req_long) == TaskType.LONG_CONTEXT_ANALYSIS
    assert router.select_platform(req_long) == "moonshot"


def test_context_manager_optimization_stub():
    ctx = AdvancedContextManager()

    # Below limit: returns unchanged
    msgs = [{"role": "user", "content": "short"}]
    out = ctx.optimize(msgs, platform="moonshot")
    assert out == msgs

    # Above limit: triggers compression stub
    very_long = "y" * (3000 * 4)  # ~3000 tokens
    msgs2 = (
        [{"role": "system", "content": "policy"}]
        + [{"role": "user", "content": very_long}] * 15
        + [{"role": "assistant", "content": "tail"}]
    )
    out2 = ctx.optimize(msgs2, platform="zai")
    # Ensure system preserved and some messages compressed
    assert any(m.get("role") == "system" for m in out2)
    assert any("[compressed" in m.get("content", "") for m in out2)


def test_error_handler_retry_and_fallback():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("boom")
        return "ok"

    h = ResilientErrorHandler(RetryPolicy(retries=3, base_delay=0.01, max_delay=0.02))
    assert h.execute(flaky) == "ok"

    # Ensure fallback used after exhausting retries
    calls2 = {"n": 0}

    def always_fail():
        calls2["n"] += 1
        raise RuntimeError("nope")

    fallback = lambda: "fb"  # noqa: E731
    assert h.execute(always_fail, fallback=fallback) == "fb"


def test_secure_input_validator_paths_and_images(tmp_path):
    # Repo root is tmp_path
    v = SecureInputValidator(repo_root=str(tmp_path))

    # Create a file inside repo
    p = tmp_path / "docs" / "file.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("hello")

    # Relative path inside root passes
    ok = v.normalize_and_check("docs/file.txt")
    assert ok.exists()

    # Escaping outside should fail
    import pytest

    with pytest.raises(ValueError):
        v.normalize_and_check("../secrets.txt")

    # Image limits
    v.validate_images([100, 200, 300], max_images=3, max_bytes=500)
    with pytest.raises(ValueError):
        v.validate_images([100, 200, 600], max_images=5, max_bytes=500)
    with pytest.raises(ValueError):
        v.validate_images([1, 2, 3, 4], max_images=3, max_bytes=500)

