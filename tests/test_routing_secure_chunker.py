import os
import importlib


def test_model_router_enabled_respects_explicit():
    os.environ["ROUTER_ENABLED"] = "true"
    os.environ["EX_ROUTING_PROFILE"] = "balanced"
    mod = importlib.import_module("utils.model_router")
    RoutingContext = getattr(mod, "RoutingContext")
    ModelRouter = getattr(mod, "ModelRouter")
    ctx = RoutingContext(tool_name="analyze", requested_model="glm-4.5")
    assert ModelRouter.decide(ctx) == "glm-4.5"


def test_secure_inputs_rejects_large_bin(tmp_path):
    from utils.secure_inputs import validate_files_for_embedding
    big = tmp_path / "file.bin"
    big.write_bytes(b"\x00" * (6 * 1024 * 1024))
    os.environ["SECURE_INPUTS_ENFORCED"] = "true"
    os.environ["SECURE_MAX_FILE_SIZE_MB"] = "5"
    os.environ["SECURE_ALLOW_ALL_EXTS"] = "false"
    msg = validate_files_for_embedding([str(big)])
    assert msg and ("File too large" in msg or "extension not allowed" in msg)


def test_chunker_basic(tmp_path):
    from utils.file_chunker import chunked_read
    os.environ["CHUNKED_READER_ENABLED"] = "true"
    p = tmp_path / "demo.py"
    p.write_text("""
class A:\n    pass\n\n# heading\n\n""" + ("def f():\n    pass\n\n" * 200))
    out = chunked_read([str(p)], max_chars=10_000, per_file_limit=2_000)
    assert out
    assert "demo.py" in out
    assert len(out) <= 10_000

