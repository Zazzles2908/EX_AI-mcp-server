"""
Kimi (Moonshot) Embeddings utility (temporary adapter).

Purpose:
- Provide a simple way to generate embeddings via Kimi's OpenAI-compatible API for interim use.
- Designed so we can later swap to external embeddings without changing downstream code.

Requirements:
- KIMI_API_KEY must be set.
- Optional: KIMI_API_URL for custom base URL (defaults to provider default).
- KIMI_EMBED_MODEL must be set to a valid embeddings model for Moonshot (e.g., consult docs/pricing).

Usage:
  # Embed a single text
  python -X utf8 tools/kimi_embeddings.py --text "hello world"

  # Embed newline-separated texts from a file
  python -X utf8 tools/kimi_embeddings.py --file dataset.txt

  # Output format: JSON lines {"index": i, "dim": <dimension>, "vector": [...]} (suppress vectors with --no-vectors)

Notes:
- This tool uses the provider registry to obtain the Kimi client. It expects OpenAI-compatible client.embeddings.create.
- In the future, we can add an --external flag to route to your own embeddings backend.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List

# Ensure project root on path for local runs
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.providers.registry import ModelProviderRegistry  # type: ignore
from src.providers.kimi import KimiModelProvider  # type: ignore


def _get_client():
    prov = ModelProviderRegistry.get_provider_for_model(os.getenv("KIMI_DEFAULT_MODEL", "kimi-latest"))
    if not isinstance(prov, KimiModelProvider):
        api_key = os.getenv("KIMI_API_KEY", "")
        if not api_key:
            raise RuntimeError("KIMI_API_KEY is not configured")
        prov = KimiModelProvider(api_key=api_key)
    client = getattr(prov, "client", None)
    if client is None:
        raise RuntimeError("Kimi provider client is unavailable")
    if not hasattr(client, "embeddings"):
        raise RuntimeError("Kimi client does not expose embeddings API in this environment")
    return client


def _read_texts(args: argparse.Namespace) -> List[str]:
    if args.text is not None:
        return [args.text]
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            return [line.rstrip("\n") for line in f if line.strip()]
    raise SystemExit("Either --text or --file is required")


def main() -> int:
    ap = argparse.ArgumentParser(description="Moonshot (Kimi) embeddings utility")
    ap.add_argument("--text", type=str, help="Single text to embed")
    ap.add_argument("--file", type=str, help="Path to a file with newline-separated texts")
    ap.add_argument("--no-vectors", action="store_true", help="Suppress vectors in output; print only dims")
    args = ap.parse_args()

    model = os.getenv("KIMI_EMBED_MODEL", "")
    if not model:
        print("ERROR: KIMI_EMBED_MODEL is not set; please set a valid Moonshot embeddings model.", file=sys.stderr)
        return 2

    texts = _read_texts(args)
    client = _get_client()

    # OpenAI-compatible: client.embeddings.create(model=..., input=[...])
    resp = client.embeddings.create(model=model, input=texts)

    # Response normalization (OpenAI-like)
    data = getattr(resp, "data", None) or getattr(resp, "embeddings", None) or []
    if not isinstance(data, list):
        # Some clients may return dict
        data = data.get("data") if isinstance(data, dict) else []

    for i, item in enumerate(data):
        vec = getattr(item, "embedding", None) or item.get("embedding") if isinstance(item, dict) else None
        dim = len(vec) if isinstance(vec, list) else None
        out = {"index": i, "dim": dim}
        if not args.no_vectors and isinstance(vec, list):
            out["vector"] = vec
        print(json.dumps(out, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

