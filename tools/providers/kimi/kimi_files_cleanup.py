"""
Kimi (Moonshot) Files cleanup utility.

Safely list and optionally delete stored files in your Moonshot account.
Default mode is dry-run (no deletions). Requires KIMI_API_KEY in your env.

Usage examples:
  # Show summary only (default dry-run)
  python -X utf8 tools/kimi_files_cleanup.py --summary

  # List all files (first 100, use --limit to change)
  python -X utf8 tools/kimi_files_cleanup.py --list --limit 200

  # Delete files created before a date (UTC), DRY-RUN by default
  python -X utf8 tools/kimi_files_cleanup.py --before 2025-09-08

  # Actually delete (remove --dry-run to perform deletions)
  python -X utf8 tools/kimi_files_cleanup.py --before 2025-09-08 --no-dry-run

  # Keep only today's files (UTC), delete everything older (dry-run)
  python -X utf8 tools/kimi_files_cleanup.py --keep-today

Notes:
- We use the Kimi provider via the unified registry when possible; otherwise fall back to the OpenAI-compatible client.
- Deletion is performed by id; we filter by created_at <= before_date (UTC midnight) when available.
- Always start with a dry-run to verify which files would be affected.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from typing import Any, Dict, List, Optional

# Auto-load .env from project root for CLI robustness
try:
    from pathlib import Path
    from dotenv import load_dotenv  # type: ignore
    _root = Path(__file__).resolve().parents[1]
    load_dotenv(dotenv_path=str(_root / ".env"))
except Exception:
    pass

# Ensure project root on path for local runs
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.providers.registry import ModelProviderRegistry  # type: ignore


def _utc_midnight(date_str: str) -> int:
    # Convert YYYY-MM-DD to Unix timestamp at 00:00:00Z
    d = dt.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
    return int(d.timestamp())


def _today_utc_midnight() -> int:
    now = dt.datetime.now(dt.timezone.utc)
    today = dt.datetime(year=now.year, month=now.month, day=now.day, tzinfo=dt.timezone.utc)
    return int(today.timestamp())


def _days_ago_utc_midnight(days: int) -> int:
    now = dt.datetime.now(dt.timezone.utc)
    target = now - dt.timedelta(days=days)
    midnight = dt.datetime(year=target.year, month=target.month, day=target.day, tzinfo=dt.timezone.utc)
    return int(midnight.timestamp())


def _get_kimi_client():
    """Return a client exposing .files.* for Kimi (Moonshot).

    Preference order:
    1) Provider registry client if it exposes .files
    2) Direct OpenAI-compatible client using KIMI_API_KEY (+ optional KIMI_API_URL)
    """
    # Try provider registry first
    try:
        prov = ModelProviderRegistry.get_provider_for_model(os.getenv("KIMI_DEFAULT_MODEL", "kimi-latest"))
        client = getattr(prov, "client", None)
        if client is not None and hasattr(client, "files"):
            return client
    except Exception:
        pass

    # Fallback: direct OpenAI-compatible client
    api_key = os.getenv("KIMI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("KIMI_API_KEY is not configured")
    base_url = os.getenv("KIMI_API_URL", "https://api.moonshot.ai/v1").strip()
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("OpenAI SDK is not available to construct a Kimi client") from e
    return OpenAI(api_key=api_key, base_url=base_url)


def _to_dict_list(data: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                out.append(item)
            else:
                # Pydantic-style object
                fid = getattr(item, "id", None) or getattr(item, "file_id", None)
                cts = getattr(item, "created_at", None) or getattr(item, "createdAt", None) or getattr(item, "created", None)
                name = getattr(item, "filename", None) or getattr(item, "name", None)
                size = getattr(item, "bytes", None) or getattr(item, "size", None)
                out.append({"id": fid, "created_at": cts, "filename": name, "bytes": size})
    elif isinstance(data, dict):
        inner = data.get("data") or []
        return _to_dict_list(inner)
    return out


def list_files(limit: int = 100) -> List[Dict[str, Any]]:
    client = _get_kimi_client()
    # OpenAI-compatible clients typically support .files.list() -> {data: [...]} or list(limit=)
    try:
        res = client.files.list(limit=limit)
    except Exception:
        res = client.files.list()
    data = getattr(res, "data", None) or getattr(res, "files", None) or res
    return _to_dict_list(data)


def delete_file(file_id: str) -> bool:
    client = _get_kimi_client()
    try:
        # OpenAI-compatible: client.files.delete(file_id=...)
        res = client.files.delete(file_id=file_id)
        ok = getattr(res, "deleted", None)
        if ok is None and isinstance(res, dict):
            ok = res.get("deleted")
        return bool(ok) if ok is not None else True
    except Exception:
        return False


def filter_before(files: List[Dict[str, Any]], threshold_ts: int) -> List[Dict[str, Any]]:
    out = []
    for f in files:
        # created_at may be int unix timestamp in seconds
        created_at = f.get("created_at") or f.get("createdAt") or f.get("created")
        try:
            created_ts = int(created_at)
        except Exception:
            created_ts = None
        if created_ts is not None and created_ts < threshold_ts:
            out.append(f)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Moonshot (Kimi) files cleanup utility")
    ap.add_argument("--list", action="store_true", help="List files (limited)")
    ap.add_argument("--limit", type=int, default=100, help="Max files to list")
    ap.add_argument("--summary", action="store_true", help="Print summary counts only")
    ap.add_argument("--before", type=str, help="Delete files created before YYYY-MM-DD (UTC)")
    ap.add_argument("--keep-today", action="store_true", help="Delete all files older than today (UTC)")
    ap.add_argument("--older-than-days", type=int, help="Delete files older than N days (UTC)")
    ap.add_argument("--no-dry-run", dest="dry_run", action="store_false", default=True, help="Perform actual deletion")
    args = ap.parse_args()

    try:
        files = list_files(limit=max(1000, args.limit) if (args.before or args.keep_today or args.older_than_days is not None) else args.limit)
    except Exception as e:
        print(f"ERROR: Unable to list files: {e}", file=sys.stderr)
        return 2

    if args.summary and not (args.before or args.keep_today or args.list):
        print(f"Total files (first {args.limit}): {len(files)}")
        return 0

    if args.list and not (args.before or args.keep_today):
        for f in files:
            fid = f.get("id") or f.get("file_id") or "<no-id>"
            cts = f.get("created_at") or f.get("createdAt") or f.get("created")
            name = f.get("filename") or f.get("name") or "<unnamed>"
            print(f"{fid}\t{cts}\t{name}")
        return 0

    # Deletion path (dry-run by default)
    if args.keep_today:
        threshold_ts = _today_utc_midnight()
    elif args.before:
        threshold_ts = _utc_midnight(args.before)
    elif args.older_than_days is not None:
        threshold_ts = _days_ago_utc_midnight(args.older_than_days)
    else:
        ap.error("No action specified. Use --list/--summary or --before/--keep-today/--older-than-days.")
        return 2

    victims = filter_before(files, threshold_ts)
    print(f"Matched {len(victims)} files before {threshold_ts} (UTC). Dry-run={args.dry_run}")

    errors = 0
    deleted = 0
    for f in victims:
        fid = f.get("id") or f.get("file_id")
        name = f.get("filename") or f.get("name") or "<unnamed>"
        cts = f.get("created_at") or f.get("createdAt") or f.get("created")
        if not fid:
            continue
        if args.dry_run:
            print(f"DRY-RUN delete: {fid}\t{cts}\t{name}")
        else:
            ok = delete_file(fid)
            if ok:
                print(f"Deleted: {fid}\t{cts}\t{name}")
                deleted += 1
            else:
                print(f"ERROR deleting: {fid}\t{cts}\t{name}", file=sys.stderr)
                errors += 1

    if not args.dry_run:
        print(f"Deletion complete. Deleted={deleted}, Errors={errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

