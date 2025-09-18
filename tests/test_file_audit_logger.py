import json
from pathlib import Path
from audit.file_audit_logger import FileAuditLogger


def test_file_audit_logger_writes():
    path = Path("logs/test_audit.log")
    if path.exists():
        path.unlink()
    a = FileAuditLogger(path=str(path), max_bytes=10_000)
    a.log("u", "analyze", {"x": 1}, True)
    content = path.read_text(encoding="utf-8").strip()
    assert content
    rec = json.loads(content)
    assert rec["user"] == "u" and rec["tool"] == "analyze"

