"""GLM (ZhipuAI) model provider implementation."""

# DEPRECATION (Phase B): New code should import from src.providers.glm.
# This legacy module remains for compatibility; functionality is unchanged.

import logging
import os
from typing import Optional

from .base import (
    ModelCapabilities,
    ModelResponse,
    ProviderType,
    RangeTemperatureConstraint,
)
from .openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class GLMModelProvider(OpenAICompatibleProvider):
    """GLM (ZhipuAI) model provider implementation.

    Provides access to ZhipuAI's GLM models through their OpenAI-compatible API.
    Supports various GLM model variants including GLM-4, GLM-4-Plus, and GLM-Air series.
    """

    FRIENDLY_NAME = "GLM"

    # Define supported GLM models with their capabilities
    SUPPORTED_MODELS = {
        "glm-4": ModelCapabilities(
            provider=ProviderType.GLM,
            model_name="glm-4",
            friendly_name="GLM-4",
            context_window=128_000,
            max_output_tokens=64_000,
            supports_extended_thinking=False,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.95),
            description="Standard GLM-4 model for general tasks with 128K context",
            aliases=["glm", "zhipu"],
        ),
        "glm-4-plus": ModelCapabilities(
            provider=ProviderType.GLM,
            model_name="glm-4-plus",
            friendly_name="GLM-4 Plus",
            context_window=128_000,
            max_output_tokens=64_000,
            supports_extended_thinking=False,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.95),
            description="Enhanced GLM-4 model with improved capabilities",
            aliases=["glm-plus"],
        ),
        "glm-4-air": ModelCapabilities(
            provider=ProviderType.GLM,
            model_name="glm-4-air",
            friendly_name="GLM-4 Air",
            context_window=128_000,
            max_output_tokens=64_000,
            supports_extended_thinking=False,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.95),
            description="Lightweight GLM-4 model optimized for speed",
            aliases=["glm-air", "glm-4.5-airx"],
        ),
        "glm-4.5": ModelCapabilities(
            provider=ProviderType.GLM,
            model_name="glm-4.5",
            friendly_name="GLM-4.5",
            context_window=200_000,
            max_output_tokens=100_000,
            supports_extended_thinking=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.95),
            description="Latest GLM model with enhanced capabilities, 200K context, and Deep Thinking mode",
            aliases=["GLM-4.5", "glm-4.5v"],
        ),
        # Alias capturing a 256K-capable variant if available under your account
        # Placeholder for a 256K-capable GLM variant can be added here once publicly available model IDs are confirmed.
        # Example (disabled):
        # "glm-4.5-256k-preview": ModelCapabilities(
        #     provider=ProviderType.GLM,
        #     model_name="glm-4.5-256k-preview",
        #     friendly_name="GLM-4.5 (256K Preview)",
        #     context_window=256_000,
        #     max_output_tokens=128_000,
        #     supports_extended_thinking=False,
        #     temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.95),
        #     description="256K context (preview) – requires provider access",
        #     aliases=["glm-4.5-256k"],
        # ),
        "glm-4.5-air": ModelCapabilities(
            provider=ProviderType.GLM,
            model_name="glm-4.5-air",
            friendly_name="GLM-4.5 Air",
            context_window=200_000,
            max_output_tokens=100_000,
            supports_extended_thinking=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.95),
            description="Lightweight GLM-4.5 model optimized for speed with 200K context; supports Deep Thinking",
            aliases=["GLM-4.5-Air", "GLM-4-Air-250414", "glm-4.5-x"],
        ),
        "glm-4.5-flash": ModelCapabilities(
            provider=ProviderType.GLM,
            model_name="glm-4.5-flash",
            friendly_name="GLM-4.5 Flash",
            context_window=200_000,
            max_output_tokens=100_000,
            supports_extended_thinking=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.95),
            description="Ultra-fast GLM-4.5 model for quick responses with 200K context; supports Deep Thinking",
            aliases=["GLM-4.5-Flash", "GLM-4-Flash-250414"],
        ),
        # Note: GLM-4.5-Pro not yet generally available; keep alias-only resolution disabled for now
        # Mapping of legacy/prospective names handled via alias resolution below
        # Alternative naming conventions
        "GLM-4": ModelCapabilities(
            provider=ProviderType.GLM,
            model_name="GLM-4",
            friendly_name="GLM-4 (Alt)",
            context_window=128_000,
            max_output_tokens=64_000,
            supports_extended_thinking=False,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.95),
            description="GLM-4 model with uppercase naming",
            aliases=["z-ai", "glm-4-32b-0414-128k"],
        ),
    }

    def __init__(self, api_key: str, **kwargs):
        """Initialize GLM provider with ZhipuAI API configuration.
        Prefers OpenAI-compatible path; optionally uses official SDK if installed in isolated venv.
        """
        # Prefer official ZhipuAI OpenAI-compatible endpoint by default
        kwargs.setdefault("base_url", os.getenv("GLM_API_URL", "https://open.bigmodel.cn/api/paas/v4"))
        super().__init__(api_key, **kwargs)
        self._zhipu_sdk_client = None
        use_sdk = (os.getenv("GLM_SDK_ENABLED", "false").strip().lower() == "true")
        if use_sdk:
            try:
                from .zhipu_optional import get_zhipu_client_or_none
                self._zhipu_sdk_client = get_zhipu_client_or_none(api_key, kwargs.get("base_url"))
                if self._zhipu_sdk_client:
                    logger.info("ZhipuAI SDK enabled by env and initialized")
                else:
                    logger.info("ZhipuAI SDK not available; falling back to OpenAI-compatible client")
            except Exception:
                logger.info("ZhipuAI SDK import failed; falling back to OpenAI-compatible client")
        else:
            logger.info("GLM_SDK_ENABLED=false; using OpenAI-compatible client")

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific GLM model.

        Args:
            model_name: Name of the model (can be alias)

        Returns:
            ModelCapabilities object for the model

        Raises:
            ValueError: If model is not supported or not allowed by restrictions
        """
        resolved_name = self._resolve_model_name(model_name)

        if resolved_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported GLM model: {model_name}")

        # Apply model restrictions if configured
        from utils.model_restrictions import get_restriction_service
        restriction_service = get_restriction_service()
        if not restriction_service.is_allowed(ProviderType.GLM, resolved_name, model_name):
            raise ValueError(f"GLM model '{model_name}' is not allowed by current restrictions.")

        return self.SUPPORTED_MODELS[resolved_name]

    def get_provider_type(self) -> ProviderType:
        """Get the provider type for this provider.

        Returns:
            ProviderType.GLM
        """
        return ProviderType.GLM

    def validate_model_name(self, model_name: str) -> bool:
        """Validate if a model name is supported by this provider.

        Args:
            model_name: Model name to validate (can be alias)

        Returns:
            True if model is supported, False otherwise
        """
        resolved_name = self._resolve_model_name(model_name)
        return resolved_name in self.SUPPORTED_MODELS

    def generate_content(self, prompt: str, model_name: str, **kwargs) -> ModelResponse:
        """Generate content using GLM models.
        Falls back to OpenAI-compatible client when official SDK is unavailable.
        """
        resolved_model_name = self._resolve_model_name(model_name)
        # If official SDK is available, try it first in a minimal path
        if self._zhipu_sdk_client is not None:
            try:
                messages = []
                sys_prompt = kwargs.get("system_prompt")
                if sys_prompt:
                    messages.append({"role": "system", "content": sys_prompt})
                messages.append({"role": "user", "content": prompt})
                temperature = kwargs.get("temperature", 0.3)
                max_tokens = kwargs.get("max_output_tokens")
                # Pass through provider-native tools/tool_choice if present (web browsing enablement)
                sdk_kwargs = {}
                if "tools" in kwargs and kwargs.get("tools"):
                    sdk_kwargs["tools"] = kwargs.get("tools")
                if "tool_choice" in kwargs:
                    sdk_kwargs["tool_choice"] = kwargs.get("tool_choice")
                if "stream" in kwargs:
                    sdk_kwargs["stream"] = kwargs.get("stream")
                # Apply Deep Thinking mode if requested via kwargs or env
                thinking = kwargs.get("thinking") or {}
                # allow env override (GLM_THINKING_MODE=enabled|disabled)
                glm_thinking_env = (os.getenv("GLM_THINKING_MODE","enabled").strip().lower() if hasattr(os, "getenv") else "enabled")
                if not thinking:
                    thinking = {"type": glm_thinking_env if glm_thinking_env in ("enabled","disabled") else "enabled"}
                elif isinstance(thinking, dict):
                    t = thinking.get("type")
                    if t not in ("enabled","disabled"):
                        thinking["type"] = "enabled"
                sdk_kwargs["thinking"] = thinking

                resp = self._zhipu_sdk_client.chat.completions.create(
                    model=resolved_model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **sdk_kwargs,
                )
                # Handle streaming and non-streaming uniformly
                try:
                    content = resp.choices[0].message.content
                except Exception:
                    content = getattr(resp, "content", "") or ""
                return ModelResponse(
                    content=content or "",
                    usage={},
                    model_name=resolved_model_name,
                    friendly_name=self.FRIENDLY_NAME,
                    provider=self.get_provider_type(),
                    metadata={"via": "zhipuai_sdk"},
                )
            except Exception:
                # Fall through to OpenAI-compatible path on any SDK failure
                pass
        return super().generate_content(prompt=prompt, model_name=resolved_model_name, **kwargs)

    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if a model supports extended thinking mode.

        Args:
            model_name: Name of the model to check

        Returns:
            True if model supports thinking mode, False otherwise
        """
        try:
            capabilities = self.get_capabilities(model_name)
            return capabilities.supports_extended_thinking
        except ValueError:
            return False

    def list_models(self, respect_restrictions: bool = True) -> list[str]:
        """List all available GLM models.

        Args:
            respect_restrictions: Whether to filter models based on restrictions

        Returns:
            List of available model names (including aliases)
        """
        if not respect_restrictions:
            # Return all models and their aliases
            models = list(self.SUPPORTED_MODELS.keys())
            for capabilities in self.SUPPORTED_MODELS.values():
                models.extend(capabilities.aliases)
            return models

        # Filter by restrictions
        from utils.model_restrictions import get_restriction_service
        restriction_service = get_restriction_service()

        allowed_models = []
        for model_name, capabilities in self.SUPPORTED_MODELS.items():
            if restriction_service.is_allowed(ProviderType.GLM, model_name):
                allowed_models.append(model_name)
                # Add aliases for allowed models
                for alias in capabilities.aliases:
                    if restriction_service.is_allowed(ProviderType.GLM, model_name, alias):
                        allowed_models.append(alias)

        return allowed_models

    def _resolve_model_name(self, model_name: str) -> str:
        """Resolve model aliases to actual model names.

        Args:
            model_name: Input model name or alias

        Returns:
            Resolved canonical model name
        """
        # Check if it's already a canonical model name
        # Normalize case
        name_norm = model_name.strip()
        if name_norm in self.SUPPORTED_MODELS:
            return model_name

        # Search through aliases
        for canonical_name, capabilities in self.SUPPORTED_MODELS.items():
            if name_norm in capabilities.aliases:
                logger.debug(f"Resolved GLM model alias '{model_name}' to '{canonical_name}'")
                return canonical_name

        # If no alias found, return as-is (will be caught by validation)
        return model_name
