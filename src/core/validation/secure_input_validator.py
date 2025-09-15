from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List


class SecureInputValidator:
    """Centralized validation for file paths and images.

    - Enforces containment within allowed roots (repo root + optional allowlist)
    - Supports both relative and absolute inputs
    - Limits image count/size (callers pass sizes)

    Configure additional allowed roots via env:
      EX_ALLOWED_PATH_ROOTS=/abs/dir1,/abs/dir2
    """

    def __init__(self, repo_root: str | None = None, extra_allowed_roots: Iterable[str] | None = None) -> None:
        self.repo_root = Path(repo_root or os.getcwd()).resolve()
        # Parse additional allowed roots from env and from constructor
        env_roots_csv = os.getenv("EX_ALLOWED_PATH_ROOTS", "").strip()
        env_roots = [s for s in (r.strip() for r in env_roots_csv.split(",")) if s]
        extras = list(extra_allowed_roots or [])
        self.allowed_roots: List[Path] = [Path(r).resolve() for r in env_roots + extras if r]

    @staticmethod
    def _is_within(child: Path, parent: Path) -> bool:
        """Return True if 'child' is within 'parent' (robust across platforms)."""
        try:
            child.resolve().relative_to(parent.resolve())
            return True
        except Exception:
            # Fallback: case-insensitive prefix check with normalized separators
            c = str(child.resolve()).replace("\\", "/").lower()
            p = str(parent.resolve()).replace("\\", "/").lower().rstrip("/")
            return c == p or c.startswith(p + "/")

    def normalize_and_check(self, path_str: str) -> Path:
        """Normalize an input path and ensure it is within an allowed root.

        - Relative inputs are resolved against repo_root
        - Absolute inputs are allowed only if they lie within repo_root or an allowed root
        """
        p = Path(path_str)
        if not p.is_absolute():
            p = (self.repo_root / p).resolve()
        else:
            p = p.resolve()

        allowed = [self.repo_root] + self.allowed_roots
        if not any(self._is_within(p, root) for root in allowed):
            allowed_str = ", ".join(str(r) for r in allowed)
            raise ValueError(
                f"Path escapes repository root and allowed roots: {path_str} (allowed: {allowed_str})"
            )
        return p

    def validate_images(self, sizes: Iterable[int], max_images: int = 10, max_bytes: int = 5 * 1024 * 1024) -> None:
        sizes = list(sizes)
        if len(sizes) > max_images:
            raise ValueError(f"Too many images: {len(sizes)} > {max_images}")
        for s in sizes:
            if s > max_bytes:
                raise ValueError(f"Image exceeds max size: {s} bytes > {max_bytes}")

