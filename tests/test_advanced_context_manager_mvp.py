from context.context_manager import AdvancedContextManager


def test_optimize_context_preserves_system_and_tail():
    cm = AdvancedContextManager()
    # Create a very large middle to exceed the Z.ai 128k-token limit (estimator ~1 token per 4 chars)
    msgs = (
        [{"role": "system", "content": "rules"}]
        + [{"role": "user", "content": "x" * 3000} for _ in range(250)]  # ~750k chars
    )
    out = cm.optimize_context(msgs, platform="zai")
    assert any(m.get("role") == "system" for m in out)
    # Tail limited to last 10 non-system messages when over limit
    assert sum(1 for m in out if m.get("role") != "system") <= 10

