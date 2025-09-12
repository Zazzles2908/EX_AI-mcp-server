"""Kimi (Moonshot) provider implementation."""

import base64
import json
import logging
import os
import time
from typing import Any, Optional

from .base import ModelProvider, ModelCapabilities, ModelResponse, ProviderType, create_temperature_constraint
from .openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class KimiModelProvider(OpenAICompatibleProvider):
    """Provider implementation for Kimi (Moonshot) models."""

    # API configuration
    DEFAULT_BASE_URL = os.getenv("KIMI_API_URL", "https://api.moonshot.ai/v1")
    # Simple in-process LRU for Kimi context tokens per session/tool/prefix
    _cache_tokens: dict[str, tuple[str, float]] = {}
    _cache_tokens_order: list[str] = []
    _cache_tokens_ttl: float = float(os.getenv("KIMI_CACHE_TOKEN_TTL_SECS", "1800"))
    _cache_tokens_max: int = int(os.getenv("KIMI_CACHE_TOKEN_LRU_MAX", "256"))

    # Model capabilities - extended thinking disabled by default for compliance
    SUPPORTED_MODELS: dict[str, ModelCapabilities] = {
        # Prioritize k2 preview models when allowed
        "kimi-k2-0905-preview": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="kimi-k2-0905-preview",
            friendly_name="Kimi",
            context_window=128000,
            max_output_tokens=8192,
            supports_images=True,
            max_image_size_mb=20.0,
            supports_function_calling=True,
            supports_streaming=True,
            supports_system_prompts=True,
            supports_extended_thinking=False,
            description="Kimi K2 2024-09 preview",
            aliases=["kimi-k2-0905", "kimi-k2"],
        ),
        "kimi-k2-0711-preview": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="kimi-k2-0711-preview",
            friendly_name="Kimi",
            context_window=128000,
            max_output_tokens=8192,
            supports_images=True,
            max_image_size_mb=20.0,
            supports_function_calling=True,
            supports_streaming=True,
            supports_system_prompts=True,
            supports_extended_thinking=False,
            description="Kimi K2 2024-07 preview",
            aliases=["kimi-k2-0711"],
        ),
        # Canonical moonshot v1 series
        "moonshot-v1-8k": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="moonshot-v1-8k",
            friendly_name="Kimi",
            context_window=8192,
            max_output_tokens=2048,
            supports_images=False,
            supports_function_calling=False,
            supports_streaming=True,
            supports_system_prompts=True,
            supports_extended_thinking=False,
            description="Moonshot v1 8k",
        ),
        "moonshot-v1-32k": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="moonshot-v1-32k",
            friendly_name="Kimi",
            context_window=32768,
            max_output_tokens=4096,
            supports_images=False,
            supports_function_calling=False,
            supports_streaming=True,
            supports_system_prompts=True,
            supports_extended_thinking=False,
            description="Moonshot v1 32k",
        ),

        # New models from Moonshot docs
        "kimi-k2-turbo-preview": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="kimi-k2-turbo-preview",
            friendly_name="Kimi",
            context_window=256000,
            max_output_tokens=8192,
            supports_images=True,
            max_image_size_mb=20.0,
            supports_function_calling=True,
            supports_streaming=True,
            supports_system_prompts=True,
            supports_extended_thinking=False,
            description="Kimi K2 Turbo high-speed 256k",
            aliases=["kimi-k2-turbo"],
        ),
        "moonshot-v1-128k": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="moonshot-v1-128k",
            friendly_name="Kimi",
            context_window=128000,
            max_output_tokens=8192,
            supports_images=False,
            supports_function_calling=False,
            supports_streaming=True,
            supports_system_prompts=True,
            supports_extended_thinking=False,
            description="Moonshot v1 128k",
        ),
        "moonshot-v1-8k-vision-preview": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="moonshot-v1-8k-vision-preview",
            friendly_name="Kimi",
            context_window=8192,
            max_output_tokens=2048,
            supports_images=True,
            max_image_size_mb=20.0,
            supports_function_calling=False,
            supports_streaming=True,
            supports_system_prompts=True,
            supports_extended_thinking=False,
            description="Moonshot v1 8k vision preview",
        ),
        "moonshot-v1-32k-vision-preview": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="moonshot-v1-32k-vision-preview",
            friendly_name="Kimi",
            context_window=32768,
            max_output_tokens=4096,
            supports_images=True,
            max_image_size_mb=20.0,
            supports_function_calling=False,
            supports_streaming=True,
            supports_system_prompts=True,
            supports_extended_thinking=False,
            description="Moonshot v1 32k vision preview",
        ),
        "moonshot-v1-128k-vision-preview": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="moonshot-v1-128k-vision-preview",
            friendly_name="Kimi",
            context_window=128000,
            max_output_tokens=8192,
            supports_images=True,
            max_image_size_mb=20.0,
            supports_function_calling=False,
            supports_streaming=True,
            supports_system_prompts=True,
            supports_extended_thinking=False,
            description="Moonshot v1 128k vision preview",
        ),
        "kimi-latest": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="kimi-latest",
            friendly_name="Kimi",
            context_window=128000,
            max_output_tokens=8192,
            supports_images=True,
            max_image_size_mb=20.0,
            supports_function_calling=True,
            supports_streaming=True,
            supports_system_prompts=True,
            supports_extended_thinking=False,
            description="Kimi latest vision 128k",
        ),
        "kimi-thinking-preview": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="kimi-thinking-preview",
            friendly_name="Kimi",
            context_window=128000,
            max_output_tokens=8192,
            supports_images=True,
            max_image_size_mb=20.0,
            supports_function_calling=True,
            supports_streaming=True,
            supports_system_prompts=True,
            supports_extended_thinking=True,
            description="Kimi multimodal reasoning 128k",
        ),
    }

    def __init__(self, api_key: str, base_url: Optional[str] = None, **kwargs):
        self.base_url = base_url or self.DEFAULT_BASE_URL
        # Provider-specific timeout overrides via env
        try:
            rt = os.getenv("KIMI_READ_TIMEOUT_SECS", "").strip()
            ct = os.getenv("KIMI_CONNECT_TIMEOUT_SECS", "").strip()
            wt = os.getenv("KIMI_WRITE_TIMEOUT_SECS", "").strip()
            pt = os.getenv("KIMI_POOL_TIMEOUT_SECS", "").strip()
            if rt:
                kwargs["read_timeout"] = float(rt)
            if ct:
                kwargs["connect_timeout"] = float(ct)
            if wt:
                kwargs["write_timeout"] = float(wt)
            if pt:
                kwargs["pool_timeout"] = float(pt)
            # Provide a Kimi-specific sane default if nothing configured
            if "read_timeout" not in kwargs and not rt:
                # Default to 300s to avoid multi-minute hangs on web-enabled prompts
                kwargs["read_timeout"] = float(os.getenv("KIMI_DEFAULT_READ_TIMEOUT_SECS", "300"))
        except Exception:
            pass
        super().__init__(api_key, base_url=self.base_url, **kwargs)

    def get_provider_type(self) -> ProviderType:
        return ProviderType.KIMI

    def validate_model_name(self, model_name: str) -> bool:
        # Allow aliases to pass validation
        resolved = self._resolve_model_name(model_name)
        return resolved in self.SUPPORTED_MODELS

    def supports_thinking_mode(self, model_name: str) -> bool:
        resolved = self._resolve_model_name(model_name)
        capabilities = self.SUPPORTED_MODELS.get(resolved)
        return bool(capabilities and capabilities.supports_extended_thinking)

    def list_models(self, respect_restrictions: bool = True):
        # Use base implementation with restriction awareness
        return super().list_models(respect_restrictions=respect_restrictions)

    def get_model_configurations(self) -> dict[str, ModelCapabilities]:
        # Use our static SUPPORTED_MODELS
        return self.SUPPORTED_MODELS

    def get_all_model_aliases(self) -> dict[str, list[str]]:
        # Extract aliases from the capabilities
        result = {}
        for name, caps in self.SUPPORTED_MODELS.items():
            if caps.aliases:
                result[name] = caps.aliases
        return result

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        resolved = self._resolve_model_name(model_name)
        caps = self.SUPPORTED_MODELS.get(resolved)
        if not caps:
            # Default capability if unknown model (use safe defaults)
            return ModelCapabilities(
                provider=ProviderType.KIMI,
                model_name=resolved,
                friendly_name="Kimi",
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
        # Language-aware heuristic: for CJK-heavy inputs, ~0.6 tokens/char; else ~4 chars/token
        if not text:
            return 1
        try:
            total = len(text)
            cjk = 0
            for ch in text:
                o = ord(ch)
                if (0x4E00 <= o <= 0x9FFF) or (0x3040 <= o <= 0x30FF) or (0x3400 <= o <= 0x4DBF):
                    cjk += 1
            ratio = cjk / max(1, total)
            if ratio > 0.2:
                return max(1, int(total * 0.6))
            return max(1, int(total / 4))
        except Exception:
            return max(1, len(text) // 4)

    def _lru_key(self, session_id: str, tool_name: str, prefix_hash: str) -> str:
        return f"{session_id}:{tool_name}:{prefix_hash}"

    def save_cache_token(self, session_id: str, tool_name: str, prefix_hash: str, token: str) -> None:
        try:
            k = self._lru_key(session_id, tool_name, prefix_hash)
            self._cache_tokens[k] = (token, time.time())
            self._cache_tokens_order.append(k)
            # Purge expired and over-capacity entries
            self._purge_cache_tokens()
            logger.info("Kimi cache token saved key=%s suffix=%s", k[-24:], token[-6:])
        except Exception:
            pass

    def get_cache_token(self, session_id: str, tool_name: str, prefix_hash: str) -> Optional[str]:
        try:
            k = self._lru_key(session_id, tool_name, prefix_hash)
            v = self._cache_tokens.get(k)
            if not v:
                return None
            token, ts = v
            if time.time() - ts > self._cache_tokens_ttl:
                self._cache_tokens.pop(k, None)
                return None
            return token
        except Exception:
            return None

    def _purge_cache_tokens(self) -> None:
        try:
            # TTL-based cleanup
            now = time.time()
            ttl = self._cache_tokens_ttl
            self._cache_tokens = {k: v for k, v in self._cache_tokens.items() if now - v[1] <= ttl}
            # LRU size limit
            if len(self._cache_tokens) > self._cache_tokens_max:
                # remove oldest keys
                to_remove = len(self._cache_tokens) - self._cache_tokens_max
                removed = 0
                for k in list(self._cache_tokens_order):
                    if k in self._cache_tokens:
                        self._cache_tokens.pop(k, None)
                        removed += 1
                        if removed >= to_remove:
                            break
        except Exception:
            pass


    def upload_file(self, file_path: str, purpose: str = "file-extract") -> str:
        """Upload a local file to Moonshot (Kimi) and return file_id.

        Args:
            file_path: Path to a local file
            purpose: Moonshot purpose tag (e.g., 'file-extract', 'assistants')
        Returns:
            The provider-assigned file id string
        """
        from pathlib import Path
        # Resolve relative paths from project root if not absolute
        p = Path(file_path)
        if not p.is_absolute():
            try:
                project_root = Path.cwd()
                p = (project_root / p).resolve()
            except Exception:
                p = p
        if not p.exists():
            # Friendlier message: show CWD and suggest possible path
            cwd = str(Path.cwd())
            raise FileNotFoundError(f"File not found: {file_path} (cwd={cwd})")
        # Optional client-side size guardrail (helps before provider returns 4xx)
        try:
            max_mb_env = os.getenv("KIMI_FILES_MAX_SIZE_MB", "")
            if max_mb_env:
                max_bytes = float(max_mb_env) * 1024 * 1024
                if p.stat().st_size > max_bytes:
                    raise ValueError(f"Kimi upload exceeds max size {max_mb_env} MB: {p.name}")
        except Exception:
            # Never block upload if env is malformed; rely on provider errors
            pass
        result = self.client.files.create(file=p, purpose=purpose)
        file_id = getattr(result, "id", None) or (result.get("id") if isinstance(result, dict) else None)
        if not file_id:
            raise RuntimeError("Moonshot upload did not return a file id")
        return file_id
    def _prefix_hash(self, messages: list[dict[str, Any]]) -> str:
        try:
            import hashlib
            # Serialize a stable prefix of messages (roles + first 2k chars)
            parts: list[str] = []
            for m in messages[:6]:  # limit to first few messages
                role = str(m.get("role", ""))
                content = str(m.get("content", ""))[:2048]
                parts.append(role + "\n" + content + "\n")
            joined = "\n".join(parts)
            return hashlib.sha256(joined.encode("utf-8", errors="ignore")).hexdigest()
        except Exception:
            return ""

    def chat_completions_create(self, *, model: str, messages: list[dict[str, Any]], tools: Optional[list[Any]] = None, tool_choice: Optional[Any] = None, temperature: float = 0.6, **kwargs) -> dict:
        """Wrapper that injects idempotency and Kimi context-cache headers, captures cache token, and returns normalized dict.
        """
        import logging as _log
        session_id = kwargs.get("_session_id") or kwargs.get("session_id")
        call_key = kwargs.get("_call_key") or kwargs.get("call_key")
        tool_name = kwargs.get("_tool_name") or "kimi_chat_with_tools"
        prefix_hash = self._prefix_hash(messages)

        # Build extra headers
        extra_headers = {"Msh-Trace-Mode": "on"}
        if call_key:
            extra_headers["Idempotency-Key"] = str(call_key)
        # Attach cached context token if available
        cache_token = None
        if session_id and prefix_hash:
            cache_token = self.get_cache_token(session_id, tool_name, prefix_hash)
            if cache_token:
                extra_headers["Msh-Context-Cache-Token"] = cache_token
                _log.info("Kimi attach cache token suffix=%s", cache_token[-6:])

        # Call with raw response to capture headers when possible
        content_text = ""
        raw_payload = None
        try:
            api = getattr(self.client.chat.completions, "with_raw_response", None)
            if api:
                raw = api.create(
                    model=model,
                    messages=messages,
                    tools=tools,
                    tool_choice=tool_choice,
                    temperature=temperature,
                    stream=False,
                    extra_headers=extra_headers,
                )
                # Parse JSON body
                try:
                    raw_payload = raw.parse()
                except Exception:
                    raw_payload = getattr(raw, "http_response", None)
                # Extract headers
                try:
                    hdrs = getattr(raw, "http_response", None)
                    hdrs = getattr(hdrs, "headers", None) or {}
                    token_saved = None
                    for k, v in hdrs.items():
                        lk = (k.lower() if isinstance(k, str) else str(k).lower())
                        if lk in ("msh-context-cache-token-saved", "msh_context_cache_token_saved"):
                            token_saved = v
                            break
                    if token_saved and session_id and prefix_hash:
                        self.save_cache_token(session_id, tool_name, prefix_hash, token_saved)
                except Exception:
                    pass
                # Pull content
                try:
                    choice0 = (raw_payload.choices if hasattr(raw_payload, "choices") else raw_payload.get("choices"))[0]
                    msg = getattr(choice0, "message", None) or choice0.get("message", {})
                    content_text = getattr(msg, "content", None) or msg.get("content", "")
                except Exception:
                    content_text = ""
            else:
                # Fallback without raw headers support
                resp = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools,
                    tool_choice=tool_choice,
                    temperature=temperature,
                    stream=False,
                    extra_headers=extra_headers,
                )
                raw_payload = getattr(resp, "model_dump", lambda: resp)()
                try:
                    content_text = resp.choices[0].message.content
                except Exception:
                    content_text = (raw_payload.get("choices", [{}])[0].get("message", {}) or {}).get("content", "")
        except Exception as e:
            _log.error("Kimi chat call error: %s", e)
            raise

        # Normalize usage to a plain dict to ensure JSON-serializable output
        _usage = None
        try:
            if hasattr(raw_payload, "usage"):
                u = getattr(raw_payload, "usage")
                if hasattr(u, "model_dump"):
                    _usage = u.model_dump()
                elif isinstance(u, dict):
                    _usage = u
                else:
                    _usage = {
                        "prompt_tokens": getattr(u, "prompt_tokens", None),
                        "completion_tokens": getattr(u, "completion_tokens", None),
                        "total_tokens": getattr(u, "total_tokens", None),
                    }
            elif isinstance(raw_payload, dict):
                _usage = raw_payload.get("usage")
        except Exception:
            _usage = None

        return {
            "provider": "KIMI",
            "model": model,
            "content": content_text or "",
            "tool_calls": None,
            "usage": _usage,
            "raw": getattr(raw_payload, "model_dump", lambda: raw_payload)() if hasattr(raw_payload, "model_dump") else raw_payload,
        }


    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: Optional[int] = None,
        images: Optional[list[str]] = None,
        **kwargs,
    ) -> ModelResponse:
        # Delegate to OpenAI-compatible base using Moonshot base_url
        # Ensure non-streaming by default for MCP tools
        kwargs.setdefault("stream", False)
        return super().generate_content(
            prompt=prompt,
            model_name=self._resolve_model_name(model_name),
            system_prompt=system_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            images=images,
            **kwargs,
        )
