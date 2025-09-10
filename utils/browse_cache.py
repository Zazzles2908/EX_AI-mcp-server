from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional


class BrowseCache:
    """Very small file-based cache keyed by URL sha256.

    Stores records as JSON with fields: {"url": str, "ts": float, "content": str}
    """

    def __init__(self, cache_dir: Optional[Path] = None, ttl_secs: Optional[int] = None) -> None:
        self.cache_dir = cache_dir or Path(os.getenv("BROWSE_CACHE_DIR", ".cache/browse"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_secs = ttl_secs if ttl_secs is not None else int(os.getenv("BROWSE_CACHE_TTL_SECS", "86400") or 86400)

    def _key(self, url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, url: str) -> Optional[Dict[str, Any]]:
        key = self._key(url)
        p = self._path(key)
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            ts = float(data.get("ts") or 0)
            if self.ttl_secs > 0 and (time.time() - ts) > self.ttl_secs:
                # expired
                try:
                    p.unlink(missing_ok=True)
                except Exception:
                    pass
                return None
            return data
        except Exception:
            return None

    def set(self, url: str, content: str) -> None:
        key = self._key(url)
        p = self._path(key)
        rec = {"url": url, "ts": time.time(), "content": content}
        try:
            p.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

