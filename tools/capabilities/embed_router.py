"""
Embedding router CLI for EX MCP Server (Phase 5).
- Selects provider by EMBEDDINGS_PROVIDER=external|kimi|glm (default external)
- Inputs: --text or --file (newline-separated)
- Output: JSONL per line: {"index": i, "dim": <n>, "vector": [...]} (omit vectors with --no-vectors)
"""
from __future__ import annotations

import argparse
import json
import os
from typing import List

# Auto-load .env for CLI robustness
try:
    from pathlib import Path
    from dotenv import load_dotenv  # type: ignore
    _root = Path(__file__).resolve().parents[1]
    load_dotenv(dotenv_path=str(_root / ".env"))
except Exception:
    pass

from src.embeddings.provider import get_embeddings_provider


def _read_inputs(args: argparse.Namespace) -> List[str]:
    items: List[str] = []
    if args.text:
        items.append(args.text)
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            items.extend([line.rstrip("\n") for line in f if line.strip()])
    return items


def main() -> int:
    ap = argparse.ArgumentParser(description="Embedding router CLI")
    ap.add_argument("--text", type=str, help="Single text input")
    ap.add_argument("--file", type=str, help="Path to a newline-separated file of texts")
    ap.add_argument("--no-vectors", action="store_true", help="Do not print vectors (dims only)")
    args = ap.parse_args()

    texts = _read_inputs(args)
    prov = get_embeddings_provider()
    vecs = prov.embed(texts)

    for i, v in enumerate(vecs):
        out = {"index": i, "dim": len(v)}
        if not args.no_vectors:
            out["vector"] = v
        print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

