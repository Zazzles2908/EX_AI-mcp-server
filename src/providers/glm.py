"""GLM (ZhipuAI) provider implementation."""

import json
import logging
import os
from typing import Any, Optional
from pathlib import Path
import mimetypes

from .base import ModelProvider, ModelCapabilities, ModelResponse, ProviderType
from utils.http_client import HttpClient

logger = logging.getLogger(__name__)


class GLMModelProvider(ModelProvider):
    """Provider implementation for GLM models (ZhipuAI)."""

    DEFAULT_BASE_URL = os.getenv("GLM_API_URL", "https://api.z.ai/api/paas/v4")

    SUPPORTED_MODELS: dict[str, ModelCapabilities] = {
        "glm-4.5-flash": ModelCapabilities(
            provider=ProviderType.GLM,
            model_name="glm-4.5-flash",
            friendly_name="GLM",
            context_window=128000,
            max_output_tokens=8192,
            supports_images=True,
            supports_function_calling=True,
            supports_streaming=True,
            supports_system_prompts=True,
            supports_extended_thinking=False,
            description="GLM 4.5 Flash",
            aliases=["glm-4.5-air"],
        ),
        "glm-4.5": ModelCapabilities(
            provider=ProviderType.GLM,
            model_name="glm-4.5",
            friendly_name="GLM",
            context_window=128000,
            max_output_tokens=8192,
            supports_images=True,
            supports_function_calling=True,
            supports_streaming=True,
            supports_system_prompts=True,
            supports_extended_thinking=False,
            description="GLM 4.5",
        ),
        "glm-4.5-air": ModelCapabilities(
            provider=ProviderType.GLM,
            model_name="glm-4.5-air",
            friendly_name="GLM",
            context_window=128000,
            max_output_tokens=8192,
            supports_images=True,
            supports_function_calling=True,
            supports_streaming=True,
            supports_system_prompts=True,
            supports_extended_thinking=False,
            description="GLM 4.5 Air",
            aliases=["glm-4.5-x"],
        ),
    }

    def __init__(self, api_key: str, base_url: Optional[str] = None, **kwargs):
        super().__init__(api_key, **kwargs)
        self.base_url = base_url or self.DEFAULT_BASE_URL
        # Prefer official SDK; fallback to HTTP if not available
        try:
            from zhipuai import ZhipuAI  # type: ignore
            self._use_sdk = True
            self._sdk_client = ZhipuAI(api_key=self.api_key)
        except Exception as e:
            logger.warning("zhipuai SDK unavailable or failed to init; falling back to HTTP client: %s", e)
            self._use_sdk = False
            self.client = HttpClient(self.base_url, api_key=self.api_key, api_key_header="Authorization", api_key_prefix="Bearer ")

    def get_provider_type(self) -> ProviderType:
        return ProviderType.GLM

    def validate_model_name(self, model_name: str) -> bool:
        resolved = self._resolve_model_name(model_name)
        return resolved in self.SUPPORTED_MODELS

    def supports_thinking_mode(self, model_name: str) -> bool:
        resolved = self._resolve_model_name(model_name)
        capabilities = self.SUPPORTED_MODELS.get(resolved)
        return bool(capabilities and capabilities.supports_extended_thinking)

    def list_models(self, respect_restrictions: bool = True):
        return super().list_models(respect_restrictions=respect_restrictions)

    def get_model_configurations(self) -> dict[str, ModelCapabilities]:
        return self.SUPPORTED_MODELS

    def get_all_model_aliases(self) -> dict[str, list[str]]:
        result = {}
        for name, caps in self.SUPPORTED_MODELS.items():
            if caps.aliases:
                result[name] = caps.aliases
        return result

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        resolved = self._resolve_model_name(model_name)
        caps = self.SUPPORTED_MODELS.get(resolved)
        if not caps:
            return ModelCapabilities(
                provider=ProviderType.GLM,
                model_name=resolved,
                friendly_name="GLM",
                context_window=8192,
                max_output_tokens=2048,
                supports_images=False,
                supports_function_calling=False,
                supports_streaming=True,
                supports_system_prompts=True,
                supports_extended_thinking=False,
            )
        return caps

    def count_tokens(self, text: str, model_name: str) -> int:
        # Language-aware heuristic: GLM often used with Chinese; ~0.6 tokens/char for CJK
        if not text:
            return 1
        try:
            total = len(text)
            cjk = 0
            for ch in text:
                o = ord(ch)
                # CJK Unified Ideographs + Japanese Hiragana/Katakana ranges
                if (0x4E00 <= o <= 0x9FFF) or (0x3040 <= o <= 0x30FF) or (0x3400 <= o <= 0x4DBF):
                    cjk += 1
            ratio = cjk / max(1, total)
            if ratio > 0.2:
                return max(1, int(total * 0.6))
            # ASCII/Latin heuristic
            return max(1, int(total / 4))
        except Exception:
            return max(1, len(text) // 4)

    def _build_payload(self, prompt: str, system_prompt: Optional[str], model_name: str, temperature: float, max_output_tokens: Optional[int], **kwargs) -> dict:
        resolved = self._resolve_model_name(model_name)
        effective_temp = self.get_effective_temperature(resolved, temperature)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": resolved,
            "messages": messages,
            "stream": False,
        }

        if effective_temp is not None:
            payload["temperature"] = effective_temp
        if max_output_tokens:
            payload["max_tokens"] = int(max_output_tokens)

        # Images handling placeholder
        return payload

    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        resolved = self._resolve_model_name(model_name)
        payload = self._build_payload(prompt, system_prompt, resolved, temperature, max_output_tokens, **kwargs)

        try:
            if getattr(self, "_use_sdk", False):
                # Use official SDK
                resp = self._sdk_client.chat.completions.create(
                    model=resolved,
                    messages=payload["messages"],
                    temperature=payload.get("temperature"),
                    max_tokens=payload.get("max_tokens"),
                    stream=False,
                )
                # SDK returns an object; normalize to dict-like
                raw = getattr(resp, "model_dump", lambda: resp)()
                choice0 = (raw.get("choices") or [{}])[0]
                text = ((choice0.get("message") or {}).get("content")) or ""
                usage = raw.get("usage", {})
            else:
                # HTTP fallback
                raw = self.client.post_json("/chat/completions", payload)
                text = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = raw.get("usage", {})

            return ModelResponse(
                content=text or "",
                usage={
                    "input_tokens": int(usage.get("prompt_tokens", 0)),
                    "output_tokens": int(usage.get("completion_tokens", 0)),
                    "total_tokens": int(usage.get("total_tokens", 0)),
                },
                model_name=resolved,
                friendly_name="GLM",
                provider=ProviderType.GLM,
                metadata={"raw": raw},
            )
        except Exception as e:
            logger.error("GLM generate_content failed: %s", e)
            raise

    def upload_file(self, file_path: str, purpose: str = "agent") -> str:
        """Upload a file to GLM Files API and return its file id.

        Uses native SDK when available; falls back to HTTP client otherwise.
        """
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        # Optional client-side size guardrail
        try:
            max_mb_env = os.getenv("GLM_FILES_MAX_SIZE_MB", "")
            if max_mb_env:
                max_bytes = float(max_mb_env) * 1024 * 1024
                if p.stat().st_size > max_bytes:
                    raise ValueError(f"GLM upload exceeds max size {max_mb_env} MB: {p.name}")
        except Exception:
            # If env is missing/malformed, rely on provider-side limits
            pass

        # Try SDK path first
        if getattr(self, "_use_sdk", False):
            try:
                # zhipuai SDK method name may vary across versions; try common variants
                # Preferred: files.upload(file=..., purpose=...)
                if hasattr(self._sdk_client, "files") and hasattr(self._sdk_client.files, "upload"):
                    with p.open("rb") as f:
                        res = self._sdk_client.files.upload(file=f, purpose=purpose)
                elif hasattr(self._sdk_client, "files") and hasattr(self._sdk_client.files, "create"):
                    with p.open("rb") as f:
                        res = self._sdk_client.files.create(file=f, purpose=purpose)
                else:
                    res = None

                # Extract id from SDK response (object or dict)
                file_id = None
                if res is not None:
                    file_id = getattr(res, "id", None)
                    if not file_id and hasattr(res, "model_dump"):
                        data = res.model_dump()
                        file_id = data.get("id") or data.get("data", {}).get("id")
                if file_id:
                    return str(file_id)
            except Exception as e:
                # Log at warning level and fall back to HTTP path
                logger.warning("GLM SDK upload failed, falling back to HTTP: %s", e)
                # Fall through to HTTP

        # HTTP fallback (ensure file handle is closed via context manager)
        mime, _ = mimetypes.guess_type(str(p))
        with p.open("rb") as fh:
            files = {"file": (p.name, fh, mime or "application/octet-stream")}
            # Allow configurable timeout for large uploads
            try:
                t = float(os.getenv("GLM_FILE_UPLOAD_TIMEOUT_SECS", os.getenv("FILE_UPLOAD_TIMEOUT_SECS", "120")))
            except Exception:
                t = 120.0
            logger.info("GLM upload: file=%s size=%dB timeout=%.1fs purpose=%s", p.name, p.stat().st_size, t, purpose)
            js = self.client.post_multipart("/files", files=files, data={"purpose": purpose}, timeout=t)
        file_id = js.get("id") or js.get("data", {}).get("id")
        if not file_id:
            raise RuntimeError(f"GLM upload did not return an id: {js}")
        return str(file_id)
