"""
GLM (ZhipuAI) Agent Files cleanup utility.

Safely list and optionally delete stored files in your ZhipuAI (GLM) account used by agent APIs.
Default mode is dry-run (no deletions). Requires GLM_API_KEY and GLM_API_URL in your env.

Usage examples:
  # Show summary only (default dry-run)
  python -X utf8 tools/glm_files_cleanup.py --summary

  # List files (first 200, configurable)
  python -X utf8 tools/glm_files_cleanup.py --list --limit 200

  # Delete files older than 3 days (UTC midnight), DRY-RUN by default
  python -X utf8 tools/glm_files_cleanup.py --older-than-days 3

  # Actually delete
  python -X utf8 tools/glm_files_cleanup.py --older-than-days 3 --no-dry-run

Notes:
- This uses our HttpClient against GLM_API_URL. Expected endpoints:
  GET /files (with optional pagination), DELETE /files/{file_id}
- Always start with a dry-run to verify which files would be affected.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from typing import Any, Dict, List

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

from utils.http_client import HttpClient  # type: ignore


def _days_ago_utc_midnight(days: int) -> int:
    now = dt.datetime.now(dt.timezone.utc)
    target = now - dt.timedelta(days=days)
    midnight = dt.datetime(year=target.year, month=target.month, day=target.day, tzinfo=dt.timezone.utc)
    return int(midnight.timestamp())


def _to_dict_list(data: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                out.append(item)
            else:
                # Generic object
                fid = getattr(item, "id", None) or getattr(item, "file_id", None)
                cts = getattr(item, "created_at", None) or getattr(item, "createdAt", None) or getattr(item, "created", None)
                name = getattr(item, "filename", None) or getattr(item, "name", None)
                size = getattr(item, "bytes", None) or getattr(item, "size", None)
                out.append({"id": fid, "created_at": cts, "filename": name, "bytes": size})
    elif isinstance(data, dict):
        inner = data.get("data") or data.get("files") or []
        return _to_dict_list(inner)
    return out


def _get_client() -> HttpClient:
    base_url = os.getenv("GLM_API_URL", "").strip()
    api_key = os.getenv("GLM_API_KEY", "").strip()
    if not base_url or not api_key:
        raise RuntimeError("GLM_API_URL and GLM_API_KEY must be set")
    return HttpClient(base_url=base_url, api_key=api_key)


def list_files(limit: int = 200) -> List[Dict[str, Any]]:
    client = _get_client()
    # Some APIs support pagination; we attempt a single page with limit
    try:
        res = client.get_json("/files", params={"limit": limit})
    except Exception:
        res = client.get_json("/files")
    data = res if isinstance(res, list) else res.get("data") or res.get("files") or res
    return _to_dict_list(data)


def delete_file(file_id: str) -> bool:
    client = _get_client()
    try:
        res = client.delete_json(f"/files/{file_id}")
        # If API returns a body with deleted flag; otherwise assume success on 204/200
        ok = res.get("deleted") if isinstance(res, dict) else None
        return True if ok is None else bool(ok)
    except Exception:
        return False


def filter_before(files: List[Dict[str, Any]], threshold_ts: int) -> List[Dict[str, Any]]:
    out = []
    for f in files:
        cts = f.get("created_at") or f.get("createdAt") or f.get("created")
        try:
            created_ts = int(cts)
        except Exception:
            created_ts = None
        if created_ts is not None and created_ts < threshold_ts:
            out.append(f)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="ZhipuAI (GLM) files cleanup utility")
    ap.add_argument("--list", action="store_true", help="List files (limited)")
    ap.add_argument("--limit", type=int, default=200, help="Max files to list")
    ap.add_argument("--summary", action="store_true", help="Print summary counts only")
    ap.add_argument("--older-than-days", type=int, help="Delete files older than N days (UTC)")
    ap.add_argument("--no-dry-run", dest="dry_run", action="store_false", default=True, help="Perform actual deletion")
    args = ap.parse_args()

    try:
        files = list_files(limit=args.limit)
    except Exception as e:
        print(f"ERROR: Unable to list files: {e}", file=sys.stderr)
        return 2

    if args.summary and not (args.list or args.older_than_days is not None):
        print(f"Total files (first {args.limit}): {len(files)}")
        return 0

    if args.list and args.older_than_days is None:
        for f in files:
            fid = f.get("id") or f.get("file_id") or "<no-id>"
            cts = f.get("created_at") or f.get("createdAt") or f.get("created")
            name = f.get("filename") or f.get("name") or "<unnamed>"
            print(f"{fid}\t{cts}\t{name}")
        return 0

    if args.older_than_days is None:
        ap.error("No action specified. Use --list/--summary or --older-than-days.")
        return 2

    threshold_ts = _days_ago_utc_midnight(args.older_than_days)
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

