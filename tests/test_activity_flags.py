from __future__ import annotations

import os
import asyncio
from pathlib import Path

import pytest

from tools.activity import ActivityTool


def write_log(tmp_path: Path, lines: list[str]) -> Path:
    p = tmp_path / "mcp_activity.log"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


@pytest.fixture(autouse=True)
def _restore_env(monkeypatch):
    # Ensure flags are OFF by default; tests will enable explicitly
    monkeypatch.delenv("ACTIVITY_SINCE_UNTIL_ENABLED", raising=False)
    monkeypatch.delenv("ACTIVITY_STRUCTURED_OUTPUT_ENABLED", raising=False)
    yield


def test_activity_legacy_behavior(tmp_path, monkeypatch):
    # Write sample log
    log = write_log(tmp_path, [
        "2025-09-10 08:00:00 INFO Start",
        "2025-09-10 08:10:00 TOOL_CALL analyze",
        "2025-09-10 08:20:00 DONE",
    ])
    monkeypatch.setenv("EX_ACTIVITY_LOG_PATH", str(log))

    tool = ActivityTool()
    out = asyncio.get_event_loop().run_until_complete(tool.execute({"source": "activity", "lines": 10}))
    # When flags are OFF, since/until and structured are ignored; returns plain text
    assert out and hasattr(out[0], "text")
    assert "TOOL_CALL" in out[0].text


def test_activity_since_until_filter(tmp_path, monkeypatch):
    # Enable flag
    monkeypatch.setenv("ACTIVITY_SINCE_UNTIL_ENABLED", "true")

    log = write_log(tmp_path, [
        "2025-09-10 08:00:00 INFO Start",
        "2025-09-10 08:10:00 TOOL_CALL analyze",
        "2025-09-10 08:20:00 DONE",
    ])
    monkeypatch.setenv("EX_ACTIVITY_LOG_PATH", str(log))

    tool = ActivityTool()
    out = asyncio.get_event_loop().run_until_complete(
        tool.execute({"source": "activity", "lines": 10, "since": "2025-09-10T08:05:00", "until": "2025-09-10T08:15:00"})
    )
    assert out and hasattr(out[0], "text")
    txt = out[0].text
    assert "08:10:00" in txt
    assert "08:00:00" not in txt and "08:20:00" not in txt


def test_activity_structured_output(tmp_path, monkeypatch):
    # Enable flag
    monkeypatch.setenv("ACTIVITY_STRUCTURED_OUTPUT_ENABLED", "true")

    log = write_log(tmp_path, [
        "2025-09-10 08:00:00 INFO Start",
        "2025-09-10 08:10:00 TOOL_CALL analyze",
    ])
    monkeypatch.setenv("EX_ACTIVITY_LOG_PATH", str(log))

    tool = ActivityTool()
    out = asyncio.get_event_loop().run_until_complete(
        tool.execute({"source": "activity", "lines": 10, "structured": True})
    )
    assert out and hasattr(out[0], "text")
    # JSONL with two lines
    jsonl = out[0].text.strip().splitlines()
    assert all(line.strip().startswith("{") for line in jsonl)
    assert len(jsonl) == 2

