# DEPRECATION NOTICE
# Superseded by current consolidation and EXAI MCP-first workflows.
# See docs/sweep_reports/current_exai_reviews/scripts_sweep_2025-09-15.md


#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime

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

class Console:
    @staticmethod
    def hr(char: str = "-", width: int = 60) -> None:
        print(char * width)

    @staticmethod
    def title(text: str) -> None:
        Console.hr("=")
        print(f"{text}")
        Console.hr("=")

    @staticmethod
    def section(text: str) -> None:
        Console.hr("-")
        print(text)
        Console.hr("-")

    @staticmethod
    def status(text: str) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] {text}")

    @staticmethod
    def flush() -> None:
        sys.stdout.flush()


def ensure_archive_dirs(categories: List[str]) -> None:
    for c in categories:
        (ARCHIVE / c).mkdir(parents=True, exist_ok=True)


def dry_run_grouped(batches: List[Batch], verbose: bool = False) -> None:
    Console.title("Phase 3 cleanup: DRY-RUN")
    total_present = 0
    total_missing = 0
    for b in batches:
        Console.section(f"Batch: {b.name} (category: {b.category})")
        present: List[str] = []
        missing: List[str] = []
        for rel in b.files:
            if (ROOT / rel).exists():
                present.append(rel)
            else:
                missing.append(rel)
        total_present += len(present)
        total_missing += len(missing)
        print(f"  Present: {len(present)} | Missing: {len(missing)}")
        if verbose and present:
            Console.status("Files to archive:")
            for rel in present:
                print(f"   - {rel}")
        if verbose and missing:
            Console.status("Missing (skipped):")
            for rel in missing:
                print(f"   - {rel}")
    Console.hr("=")
    print(f"Summary: {total_present} present, {total_missing} missing across {len(batches)} batch(es)")
    Console.hr("=")


def archive_files(batch: Batch) -> List[Path]:
    archived: List[Path] = []
    total = len(batch.files)
    idx = 0
    for rel in batch.files:
        idx += 1
        src = ROOT / rel
        if not src.exists():
            Console.status(f"[SKIP {idx}/{total}] Missing: {rel}")
            continue
        dest = ARCHIVE / batch.category / rel.replace(os.sep, "__")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        archived.append(src)
        Console.status(f"[ARCHIVE {idx}/{total}] {rel} -> {dest.relative_to(ROOT)}")
        Console.flush()
    return archived


def delete_files(paths: List[Path]) -> Dict[str, List[Path]]:
    deleted: List[Path] = []
    deferred_locked: List[Path] = []
    failed: List[Path] = []
    for p in paths:
        try:
            p.unlink()
            print(f"[DELETE] {p.relative_to(ROOT)}")
            deleted.append(p)
        except Exception as e:
            msg = str(e)
            # Windows lock error heuristic (WinError 32)
            if "WinError 32" in msg:
                print(f"[DEFERRED] Locked, will require process stop: {p.relative_to(ROOT)}")
                deferred_locked.append(p)
            else:
                print(f"[ERROR] Failed to delete {p}: {e}")
                failed.append(p)
    # Report any still-present paths
    still_present: List[Path] = []
    for p in paths:
        try:
            if p.exists():
                still_present.append(p)
        except Exception:
            continue
    # Summary
    print("-")
    print(f"[SUMMARY] Deleted={len(deleted)} Deferred(Locked)={len(deferred_locked)} Failed={len(failed)} StillPresent={len(still_present)}")
    return {
        "deleted": deleted,
        "deferred_locked": deferred_locked,
        "failed": failed,
        "still_present": still_present,
    }


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
    parser.add_argument("--verbose", dest="verbose", action="store_true", help="Verbose output for dry-run")

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
        dry_run_grouped(batches, verbose=args.verbose)
        return

    if args.mode == "archive":
        archived_all: List[Path] = []
        for b in batches:
            archived_all.extend(archive_files(b))
        if args.do_delete:
            summary = delete_files(archived_all)
            # Explicit callout for common Windows lock case
            if summary.get("deferred_locked"):
                print("[HINT] Some files are locked by running processes (e.g., server/shim). Stop them and re-run: archive --delete")
        return

    if args.mode == "delete":
        delete_files(all_files)
        return


if __name__ == "__main__":
    main()

