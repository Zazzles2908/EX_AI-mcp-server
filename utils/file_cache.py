from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional


class FileCache:
    """Simple sha256->provider->file_id mapping with TTL and optional persistence.

    Structure on disk:
    {
      "items": {
        "<sha256>": {
          "KIMI": {"file_id": "...", "ts": 1710000000.0},
          "GLM": {"file_id": "...", "ts": 1710000100.0}
        }
      }
    }
    """

    def __init__(self, path: Optional[Path] = None, ttl_secs: Optional[int] = None) -> None:
        self.path = path or Path(os.getenv("FILECACHE_PATH", ".cache/filecache.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_secs = ttl_secs if ttl_secs is not None else int(os.getenv("FILECACHE_TTL_SECS", "604800") or 604800)
        self._data: Dict[str, Any] = {"items": {}}
        self._load()

    def _load(self) -> None:
        try:
            if self.path.exists():
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self._data = {"items": {}}

    def _save(self) -> None:
        try:
            self.path.write_text(json.dumps(self._data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    @staticmethod
    def sha256_file(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def get(self, sha256: str, provider: str) -> Optional[str]:
        now = time.time()
        rec = self._data.get("items", {}).get(sha256, {}).get(provider)
        if not rec:
            return None
        ts = float(rec.get("ts") or 0)
        if self.ttl_secs > 0 and (now - ts) > self.ttl_secs:
            # expire
            try:
                del self._data["items"][sha256][provider]
                if not self._data["items"][sha256]:
                    del self._data["items"][sha256]
                self._save()
            except Exception:
                pass
            return None
        return rec.get("file_id")

    def set(self, sha256: str, provider: str, file_id: str) -> None:
        items = self._data.setdefault("items", {})
        per = items.setdefault(sha256, {})
        per[provider] = {"file_id": file_id, "ts": time.time()}
        self._save()

