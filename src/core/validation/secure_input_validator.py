from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


class SecureInputValidator:
    """Centralized validation for file paths and images.

    - Enforces repo-root containment
    - Rejects absolute paths outside the repo
    - Limits image count/size (callers pass sizes)
    """

    def __init__(self, repo_root: str | None = None) -> None:
        self.repo_root = Path(repo_root or os.getcwd()).resolve()

    def normalize_and_check(self, relative_path: str) -> Path:
        p = (self.repo_root / relative_path).resolve()
        if not str(p).startswith(str(self.repo_root)):
            raise ValueError(f"Path escapes repository root: {relative_path}")
        return p

    def validate_images(self, sizes: Iterable[int], max_images: int = 10, max_bytes: int = 5 * 1024 * 1024) -> None:
        sizes = list(sizes)
        if len(sizes) > max_images:
            raise ValueError(f"Too many images: {len(sizes)} > {max_images}")
        for s in sizes:
            if s > max_bytes:
                raise ValueError(f"Image exceeds max size: {s} bytes > {max_bytes}")

