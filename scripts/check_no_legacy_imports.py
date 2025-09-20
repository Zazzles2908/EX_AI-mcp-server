#!/usr/bin/env python3
"""
Legacy import blocker: fail CI if non-test code imports legacy top-level modules:
- providers.*   (use src.providers.* instead)
- routing.*     (use src/router/* or src/core/agentic/*)

Scope (checked):
- server.py
- src/** (all .py files)
- tools/** (all .py files)
- scripts/** (all .py files)

Excluded:
- tests/**
- docs/**
- examples/**
- .git, venv/.venv, __pycache__

This is intentionally strict and fast; it only scans lines that are not comments.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

LEGACY_PATTERNS = [
    re.compile(r"^\s*from\s+providers\.", re.ASCII),
    re.compile(r"^\s*import\s+providers\.", re.ASCII),
    re.compile(r"^\s*from\s+routing\.", re.ASCII),
    re.compile(r"^\s*import\s+routing\.", re.ASCII),
]

INCLUDE_DIRS = {
    ROOT / "src",
    ROOT / "tools",
    ROOT / "scripts",
}
INCLUDE_FILES = {ROOT / "server.py"}

EXCLUDE_DIR_NAMES = {"tests", "docs", "examples", ".git", "__pycache__", "venv", ".venv"}


def iter_python_files() -> Iterable[Path]:
    # Single files
    for f in INCLUDE_FILES:
        if f.exists():
            yield f
    # Directories
    for d in INCLUDE_DIRS:
        if not d.exists():
            continue
        for root, dirnames, filenames in os.walk(d):
            # prune excluded dirs in-place
            dirnames[:] = [n for n in dirnames if n not in EXCLUDE_DIR_NAMES]
            for name in filenames:
                if name.endswith(".py"):
                    yield Path(root) / name


def line_has_legacy_import(line: str) -> bool:
    s = line.strip()
    if not s or s.startswith("#"):
        return False
    for pat in LEGACY_PATTERNS:
        if pat.search(s):
            return True
    return False


def main() -> int:
    violations: list[tuple[Path, int, str]] = []
    for py in iter_python_files():
        try:
            with py.open("r", encoding="utf-8", errors="ignore") as fh:
                for i, ln in enumerate(fh, start=1):
                    if line_has_legacy_import(ln):
                        violations.append((py, i, ln.rstrip()))
        except Exception as e:
            print(f"WARN: failed to scan {py}: {e}", file=sys.stderr)

    if violations:
        print("Legacy imports detected (providers.* or routing.*) in non-test code:")
        for path, lineno, text in violations:
            rel = path.relative_to(ROOT)
            print(f"  {rel}:{lineno}: {text}")
        print("\nFix: replace with src.providers.* or src/router/* (or src/core/agentic/*).", file=sys.stderr)
        return 1

    print("OK: no legacy imports found in non-test code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

