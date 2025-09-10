"""Kimi (Moonshot) provider implementation."""

import base64
import json
import logging
import os
from typing import Any, Optional

from .base import ModelProvider, ModelCapabilities, ModelResponse, ProviderType, create_temperature_constraint
from .openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class KimiModelProvider(OpenAICompatibleProvider):
    """Provider implementation for Kimi (Moonshot) models."""

    # API configuration
    DEFAULT_BASE_URL = os.getenv("KIMI_API_URL", "https://api.moonshot.ai/v1")

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
