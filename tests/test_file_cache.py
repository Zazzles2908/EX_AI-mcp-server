import os
import time
import json
from pathlib import Path
import tempfile

import pytest

from utils.file_cache import FileCache


def write_temp_file(dirpath: Path, name: str, content: bytes) -> Path:
    p = dirpath / name
    p.write_bytes(content)
    return p


def test_filecache_set_get_persist_and_ttl_expiry(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        cache_path = d / "filecache.json"
        monkeypatch.setenv("FILECACHE_PATH", str(cache_path))
        # small TTL for test
        fc = FileCache(ttl_secs=1)

        # Create a temp file and compute sha
        f = write_temp_file(d, "a.txt", b"hello world")
        sha = FileCache.sha256_file(f)

        # Initially miss
        assert fc.get(sha, "KIMI") is None

        # Set mapping and persist
        fc.set(sha, "KIMI", "file_123")
        assert fc.get(sha, "KIMI") == "file_123"

        # New instance should load persisted data
        fc2 = FileCache(ttl_secs=1)
        assert fc2.get(sha, "KIMI") == "file_123"

        # Wait for TTL to expire
        time.sleep(1.2)
        assert fc2.get(sha, "KIMI") is None


def test_sha256_file_is_stable():
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "data.bin"
        data = b"abc" * 1000
        p.write_bytes(data)
        s1 = FileCache.sha256_file(p)
        s2 = FileCache.sha256_file(p)
        assert s1 == s2


def test_env_configurable_path_and_ttl(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        custom_path = d / "custom.json"
        monkeypatch.setenv("FILECACHE_PATH", str(custom_path))
        monkeypatch.setenv("FILECACHE_TTL_SECS", "123")
        fc = FileCache()
        assert fc.ttl_secs == 123
        # Write and ensure file exists at custom path
        fc.set("deadbeef", "GLM", "fid-1")
        assert custom_path.exists()
        # JSON structure basic check
        obj = json.loads(custom_path.read_text(encoding="utf-8"))
        assert "items" in obj
        assert "deadbeef" in obj["items"]

