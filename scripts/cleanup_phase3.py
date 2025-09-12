#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "archive"
MANIFEST = ROOT / "docs" / "cleanup" / "phase3_manifest.json"

@dataclass
class Batch:
    name: str
    category: str
    files: List[str]


def load_manifest() -> List[Batch]:
    with MANIFEST.open("r", encoding="utf-8") as f:
        data = json.load(f)
    batches = []
    for b in data.get("batches", []):
        batches.append(Batch(name=b["name"], category=b["category"], files=b.get("files", [])))
    return batches


def ensure_archive_dirs(categories: List[str]) -> None:
    for c in categories:
        (ARCHIVE / c).mkdir(parents=True, exist_ok=True)


def dry_run(files: List[Path]) -> None:
    print("[DRY-RUN] The following files would be archived:")
    for f in files:
        print(f" - {f.relative_to(ROOT)}")


def archive_files(batch: Batch) -> List[Path]:
    archived: List[Path] = []
    for rel in batch.files:
        src = ROOT / rel
        if not src.exists():
            print(f"[WARN] Skipping missing: {rel}")
            continue
        dest = ARCHIVE / batch.category / rel.replace(os.sep, "__")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        archived.append(src)
        print(f"[ARCHIVE] {rel} -> {dest.relative_to(ROOT)}")
    return archived


def delete_files(paths: List[Path]) -> None:
    for p in paths:
        try:
            p.unlink()
            print(f"[DELETE] {p.relative_to(ROOT)}")
        except Exception as e:
            print(f"[ERROR] Failed to delete {p}: {e}")


def restore_batch(batch_name: str) -> None:
    # Find batch
    batches = load_manifest()
    batch = next((b for b in batches if b.name == batch_name), None)
    if not batch:
        raise SystemExit(f"Batch not found: {batch_name}")

    for rel in batch.files:
        dest = ROOT / rel
        src = ARCHIVE / batch.category / rel.replace(os.sep, "__")
        if not src.exists():
            print(f"[WARN] Archive source missing: {src}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        print(f"[RESTORE] {src.relative_to(ROOT)} -> {rel}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3 cleanup helper (archive-first)")
    parser.add_argument("mode", choices=["dry-run", "archive", "delete", "restore"], help="Operation mode")
    parser.add_argument("--batch", dest="batch", help="Specific batch name for restore")
    parser.add_argument("--delete", dest="do_delete", action="store_true", help="After archive, perform deletion")
    args = parser.parse_args()

    batches = load_manifest()
    ensure_archive_dirs([b.category for b in batches])

    if args.mode == "restore":
        if not args.batch:
            raise SystemExit("--batch is required for restore mode")
        restore_batch(args.batch)
        return

    all_files = [ROOT / rel for b in batches for rel in b.files]

    if args.mode == "dry-run":
        dry_run(all_files)
        return

    if args.mode == "archive":
        archived_all: List[Path] = []
        for b in batches:
            archived_all.extend(archive_files(b))
        if args.do_delete:
            delete_files(archived_all)
        return

    if args.mode == "delete":
        delete_files(all_files)
        return


if __name__ == "__main__":
    main()

