from tools.unified.chaining import ChainRunner


def test_chain_runner_threads_context():
    def s1(ctx):
        return {"a": 1}

    def s2(ctx):
        return {"b": ctx.get("a", 0) + 1}

    cr = ChainRunner([s1, s2])
    out = cr.run({})
    assert out["a"] == 1 and out["b"] == 2

