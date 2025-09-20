#!/usr/bin/env python
"""
Fail the build if any non-test source file imports legacy top-level modules:
- providers.* or routing.*

Exclusions:
- tests/**
- providers/** (shim tree)
- routing/** (shim tree)
- .venv, venv, .git, dist, build, __pycache__, docs/**

Usage:
  python scripts/check_no_legacy_imports.py

Exit code 0: OK
Exit code 1: Violations found
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_DIRS = {
    "tests",
    "providers",
    "routing",
    ".git",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
    "docs",
}

PYTHON_EXT = {".py"}

PATTERN = re.compile(r"^\s*(?:from\s+(providers|routing)\b|import\s+(providers|routing)\b)")

violations: list[tuple[str, int, str]] = []

for path in ROOT.rglob("*.py"):
    rel = path.relative_to(ROOT).as_posix()
    # Skip excluded directories
    parts = rel.split("/")
    if parts[0] in EXCLUDED_DIRS:
        continue
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for lineno, line in enumerate(text.splitlines(), start=1):
        if PATTERN.search(line):
            violations.append((rel, lineno, line.strip()))

if violations:
    print("[NO_LEGACY_IMPORTS] Found legacy imports in non-test code:")
    for rel, lineno, src in violations:
        print(f" - {rel}:{lineno}: {src}")
    print("\nFix: import from src.providers.* or src.router.* instead; routing shim exists only for backwards compatibility.")
    sys.exit(1)

print("[NO_LEGACY_IMPORTS] OK — no legacy imports found in non-test code.")

