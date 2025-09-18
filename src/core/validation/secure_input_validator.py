from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


class SecureInputValidator:
    """Centralized validation for file paths and images.

    - Enforces repo-root containment
    - Rejects absolute paths outside the repo (unless explicitly allowlisted)
    - Limits image count/size (callers pass sizes)
    """

    def __init__(self, repo_root: str | None = None) -> None:
        self.repo_root = Path(repo_root or os.getcwd()).resolve()
        # Optional, explicit allowlist for external absolute paths (opt-in, disabled by default)
        self._allow_external = str(os.getenv("EX_ALLOW_EXTERNAL_PATHS", "false")).lower() == "true"
        prefixes = os.getenv("EX_ALLOWED_EXTERNAL_PREFIXES", "")
        self._allowed_prefixes: list[Path] = []
        for raw in [p.strip() for p in prefixes.split(",") if p.strip()]:
            try:
                self._allowed_prefixes.append(Path(raw).resolve())
            except Exception:
                # Ignore malformed entries silently to avoid breaking calls
                continue

    def _is_allowed_external(self, p: Path) -> bool:
        if not self._allow_external:
            return False
        sp = str(p)
        for pref in self._allowed_prefixes:
            try:
                if sp.startswith(str(pref)):
                    return True
            except Exception:
                continue
        return False

    def normalize_and_check(self, relative_path: str) -> Path:
        # If user provided an absolute path, Path concatenation will keep it absolute
        p = (self.repo_root / relative_path).resolve()
        if not str(p).startswith(str(self.repo_root)):
            # Permit only when explicitly allowlisted via env
            if self._is_allowed_external(p):
                return p
            raise ValueError(f"Path escapes repository root: {relative_path}")
        return p

    def validate_images(self, sizes: Iterable[int], max_images: int = 10, max_bytes: int = 5 * 1024 * 1024) -> None:
        sizes = list(sizes)
        if len(sizes) > max_images:
            raise ValueError(f"Too many images: {len(sizes)} > {max_images}")
        for s in sizes:
            if s > max_bytes:
                raise ValueError(f"Image exceeds max size: {s} bytes > {max_bytes}")

