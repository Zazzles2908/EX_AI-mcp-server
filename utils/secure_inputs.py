from __future__ import annotations

import os
import mimetypes
from pathlib import Path
from typing import Iterable, Optional

# Secure input validation for tool file embeddings
# Env knobs (with defaults):
# - SECURE_INPUTS_ENFORCED=true|false (default true)
# - SECURE_MAX_FILE_SIZE_MB=int (default 5)
# - SECURE_MAX_TOTAL_EMBED_MB=int (default 20)
# - SECURE_ALLOWED_EXTS=comma list (default common code/text)
# - SECURE_ALLOW_ALL_EXTS=true|false (default false)


DEFAULT_ALLOWED_EXTS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".txt",
    ".toml", ".yaml", ".yml", ".ini", ".cfg", ".sh", ".ps1", ".bat",
    ".java", ".kt", ".go", ".rs", ".rb", ".php", ".cs",
    ".cpp", ".cc", ".c", ".h", ".hpp",
}


def _bool_env(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() == "true"


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _allowed_exts() -> set[str]:
    if _bool_env("SECURE_ALLOW_ALL_EXTS", False):
        return set()
    raw = os.getenv("SECURE_ALLOWED_EXTS")
    if not raw:
        return set(DEFAULT_ALLOWED_EXTS)
    return {x.strip().lower() for x in raw.split(",") if x.strip()}


def _is_binary(path: Path) -> bool:
    # Quick checks: extension and mime
    mt, _ = mimetypes.guess_type(str(path))
    if mt:
        if not (mt.startswith("text/") or mt in ("application/json", "application/xml")):
            # Could still be text (e.g., unknown), keep checking below
            pass
    try:
        with open(path, "rb") as f:
            chunk = f.read(4096)
            if b"\x00" in chunk:
                return True
            # Heuristic: if UTF-8 decode fails badly, likely binary
            try:
                chunk.decode("utf-8")
                return False
            except UnicodeDecodeError:
                # allow latin-1 text-like
                try:
                    chunk.decode("latin-1")
                    return False
                except Exception:
                    return True
    except Exception:
        # If we cannot read, be conservative but do not block here; upstream will handle
        return False
    return False


def validate_files_for_embedding(files: Iterable[str]) -> Optional[str]:
    """Validate files against security and size policy.

    Returns an error message string if validation fails, otherwise None.
    """
    if not _bool_env("SECURE_INPUTS_ENFORCED", True):
        return None

    files = [str(f) for f in files]
    # Allowed extensions
    allowed = _allowed_exts()
    if allowed:
        for f in files:
            ext = Path(f).suffix.lower()
            if ext and ext not in allowed:
                return (
                    f"File extension not allowed: '{f}'. Allowed extensions can be overridden via SECURE_ALLOWED_EXTS, "
                    f"or set SECURE_ALLOW_ALL_EXTS=true to disable this check."
                )

    # Size caps
    per_mb = _int_env("SECURE_MAX_FILE_SIZE_MB", 5)
    total_mb = _int_env("SECURE_MAX_TOTAL_EMBED_MB", 20)
    per_bytes = per_mb * 1024 * 1024
    total_bytes = total_mb * 1024 * 1024

    total = 0
    for f in files:
        p = Path(f)
        try:
            if not p.exists() or not p.is_file():
                # Non-existent or non-file is handled elsewhere; skip here
                continue
            size = p.stat().st_size
            if size > per_bytes:
                return (
                    f"File too large ({size/1_048_576:.1f}MB > {per_mb}MB cap): '{f}'. "
                    f"Reduce file size or increase SECURE_MAX_FILE_SIZE_MB."
                )
            total += size
            if total > total_bytes:
                return (
                    f"Total embedded size too large ({total/1_048_576:.1f}MB > {total_mb}MB cap). "
                    f"Reduce number of files or increase SECURE_MAX_TOTAL_EMBED_MB."
                )
        except Exception:
            # Non-fatal here
            continue

    # Binary reject by default
    if not _bool_env("SECURE_ALLOW_ALL_EXTS", False):
        for f in files:
            p = Path(f)
            try:
                if p.exists() and p.is_file() and _is_binary(p):
                    return (
                        f"Binary file rejected: '{f}'. Enable SECURE_ALLOW_ALL_EXTS=true to bypass, "
                        f"or provide text/code files only."
                    )
            except Exception:
                continue

    return None

