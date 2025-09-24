"""
Environment helpers for EX-AI MCP Server.
Additive module; safe to import even without python-dotenv installed.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Optional dotenv support (no-op if unavailable)
try:  # pragma: no cover
    from dotenv import load_dotenv as _load_dotenv
except Exception:  # pragma: no cover
    def _load_dotenv(*args, **kwargs):
        return False


TRUE_SET = {"1", "true", "yes", "on"}


class EnvHelper:
    """Helper for environment variable management with optional .env loading."""

    def __init__(self):
        self._loaded = False

    def load_dotenv(self, env_path: Optional[str] = None) -> None:
        """Load environment variables from .env file if present."""
        if self._loaded:
            return
        if env_path and Path(env_path).exists():
            _load_dotenv(env_path)
            self._loaded = True
            return
        # Try common locations relative to CWD
        for loc in (".env", "./.env", "./config/.env"):
            if Path(loc).exists():
                _load_dotenv(loc)
                self._loaded = True
                return

    def hot_reload(self, env_path: Optional[str] = None) -> None:
        """Quick hot-reload of .env (best-effort; never raises)."""
        try:
            self._loaded = False
            self.load_dotenv(env_path)
        except Exception:
            pass

    def get(self, key: str, default: Any = None, required: bool = False) -> Any:
        val = os.getenv(key, default)
        if required and (val is None or val == ""):
            raise ValueError(f"Required environment variable '{key}' is missing")
        return val

    def get_bool(self, key: str, default: bool = False) -> bool:
        val = str(self.get(key, str(default))).strip().lower()
        return val in TRUE_SET

    def get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(str(self.get(key, str(default))).strip())
        except Exception as e:
            raise ValueError(f"Invalid integer value for '{key}': {e}")

    def get_list(self, key: str, default: Optional[List[str]] = None, sep: str = ",") -> List[str]:
        if default is None:
            default = []
        raw = str(self.get(key, ""))
        if not raw:
            return default
        return [s.strip() for s in raw.split(sep) if s.strip()]

    def get_provider_keys(self) -> Dict[str, str]:
        # Optional keys; do not enforce required=True here to avoid hard failures
        return {
            "kimi": str(self.get("KIMI_API_KEY", "")),
            "glm": str(self.get("GLM_API_KEY", "")),
            "openrouter": str(self.get("OPENROUTER_API_KEY", "")),
        }

    def get_model_defaults(self) -> Dict[str, str]:
        return {
            "default": str(self.get("DEFAULT_MODEL", "auto")),
            "kimi_default": str(self.get("KIMI_DEFAULT_MODEL", "kimi-k2-0905-preview")),
            "glm_default": str(self.get("GLM_DEFAULT_MODEL", "glm-4.5-flash")),
            "glm_quality": str(self.get("GLM_QUALITY_MODEL", "glm-4.5")),
            "kimi_quality": str(self.get("KIMI_QUALITY_MODEL", "kimi-k2-0905-preview")),
        }

    def get_feature_flags(self) -> Dict[str, bool]:
        return {
            "ai_manager": self.get_bool("ENABLE_AI_MANAGER", True),
            "web_search": self.get_bool("ENABLE_WEB_SEARCH", True),
            "file_upload": self.get_bool("ENABLE_FILE_UPLOAD", True),
            "fallback": self.get_bool("ENABLE_FALLBACK", True),
        }

    def get_server_config(self) -> Dict[str, Any]:
        return {
            "name": str(self.get("MCP_SERVER_NAME", "exai")),
            "host": str(self.get("EXAI_WS_HOST", "127.0.0.1")),
            "port": self.get_int("EXAI_WS_PORT", 8765),
            "log_level": str(self.get("LOG_LEVEL", "INFO")),
            "log_file": str(self.get("LOG_FILE", "")),
            "json_logs": self.get_bool("LOG_FORMAT_JSON", False),
        }


env = EnvHelper()

