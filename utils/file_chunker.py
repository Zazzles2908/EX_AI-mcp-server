"""
Lightweight file chunker for large files.

When enabled, extracts salient sections (headings, class/def blocks, and surrounding context)
so prompts remain within token budgets. This is a conservative, opt-in utility.

Environment toggle:
- CHUNKED_READER_ENABLED=true|false (default: false)

Usage:
- chunked_read(files, max_chars=80_000, per_file_limit=20_000) -> str
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, List


SECTION_RE = re.compile(r"^(class\s+\w+|def\s+\w+|#+\s+.+)$")


def _read_text(path: Path, max_chars: int | None = None) -> str:
    try:
        txt = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        try:
            txt = path.read_text(encoding="latin-1", errors="ignore")
        except Exception:
            return ""
    if max_chars and len(txt) > max_chars:
        return txt[:max_chars]
    return txt


def _extract_salient_sections(text: str, per_file_limit: int) -> str:
    if len(text) <= per_file_limit:
        return text
    lines = text.splitlines()
    indices: List[int] = []
    for i, ln in enumerate(lines):
        if SECTION_RE.match(ln.strip()):
            indices.append(i)
    if not indices:
        return text[:per_file_limit]
    # Greedy selection of top segments around section headers
    chunks: List[str] = []
    budget = per_file_limit
    window = 80  # lines around header
    for idx in indices[:200]:  # cap sections
        start = max(0, idx - window)
        end = min(len(lines), idx + window)
        seg = "\n".join(lines[start:end])
        if not seg:
            continue
        take = seg[: min(len(seg), budget)]
        chunks.append(take)
        budget -= len(take)
        if budget <= 0:
            break
    res = "\n\n".join(chunks)
    return res[:per_file_limit]


def chunked_read(files: Iterable[str], max_chars: int = 80_000, per_file_limit: int = 20_000) -> str:
    if os.getenv("CHUNKED_READER_ENABLED", "false").strip().lower() != "true":
        return ""  # disabled, caller should fall back to normal read
    out: List[str] = []
    used = 0
    for f in files:
        p = Path(f)
        if not p.exists() or not p.is_file():
            continue
        remaining = max(0, max_chars - used)
        if remaining == 0:
            break
        raw = _read_text(p, max_chars=remaining)
        excerpt = _extract_salient_sections(raw, min(per_file_limit, remaining))
        if excerpt:
            header = f"\n\n=== {p.name} (chunked) ===\n"
            out.append(header + excerpt)
            used += len(excerpt)
    return "".join(out)
