"""Kimi (Moonshot AI) model provider implementation."""

# DEPRECATION (Phase B): New code should import from src.providers.kimi.
# This legacy module remains for compatibility; functionality is unchanged.

import logging
from typing import Optional

from .base import (
    ModelCapabilities,
    ModelResponse,
    ProviderType,
    RangeTemperatureConstraint,
)
from .openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class KimiModelProvider(OpenAICompatibleProvider):
    """Kimi (Moonshot AI) model provider implementation.

    Provides access to Moonshot AI's Kimi models through their OpenAI-compatible API.
    Supports various Kimi model variants including standard, turbo, and thinking modes.
    """

    FRIENDLY_NAME = "Kimi"

    # Define supported Kimi models with their capabilities
    SUPPORTED_MODELS = {
        "moonshot-v1-8k": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="moonshot-v1-8k",
            friendly_name="Moonshot v1 8K",
            context_window=8_000,
            max_output_tokens=4_000,
            supports_extended_thinking=False,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.3),
            description="Fast model for simple tasks with 8K context",
            aliases=["kimi-fast", "moonshot-8k"],
        ),
        "moonshot-v1-32k": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="moonshot-v1-32k",
            friendly_name="Moonshot v1 32K",
            context_window=32_000,
            max_output_tokens=16_000,
            supports_extended_thinking=False,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.3),
            description="Balanced model for general tasks with 32K context",
            aliases=["kimi", "moonshot", "moonshot-32k"],
        ),
        "moonshot-v1-128k": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="moonshot-v1-128k",
            friendly_name="Moonshot v1 128K",
            context_window=128_000,
            max_output_tokens=64_000,
            supports_extended_thinking=False,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.3),
            description="Large context model for complex analysis with 128K context",
            aliases=["kimi-turbo", "moonshot-128k"],
        ),
        "moonshot-v1-auto": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="moonshot-v1-auto",
            friendly_name="Moonshot v1 Auto",
            context_window=128_000,
            max_output_tokens=64_000,
            supports_extended_thinking=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.3),
            description="Auto-scaling model with thinking capabilities",
            aliases=["kimi-thinking", "moonshot-auto"],
        ),
        # K2 series models (newer generation) - use canonical Moonshot IDs as primary keys
        "kimi-k2-0711-preview": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="kimi-k2-0711-preview",
            friendly_name="Kimi K2 (0711 preview)",
            context_window=131_072,
            max_output_tokens=100_000,
            supports_extended_thinking=False,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.3),
            description="Latest generation Kimi model (official preview) with ~128K context",
            aliases=["kimi-k2"],
        ),
        "kimi-k2-turbo-preview": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="kimi-k2-turbo-preview",
            friendly_name="Kimi K2 Turbo (preview)",
            context_window=262_144,
            max_output_tokens=100_000,
            supports_extended_thinking=False,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.3),
            description="High-speed K2 variant (official preview) with ~256K context",
            aliases=["kimi-k2-turbo"],
        ),
        # Newer K2 preview with 256K context
        "kimi-k2-0905-preview": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="kimi-k2-0905-preview",
            friendly_name="Kimi K2 (0905 preview)",
            context_window=262_144,
            max_output_tokens=100_000,
            supports_extended_thinking=False,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.3),
            description="Latest K2 preview with 256K context window",
            aliases=["kimi-k2-0905"],
        ),
        # Convenience alias capturing a thinking-oriented profile that routes to the canonical 0711 preview
        "kimi-k2-thinking": ModelCapabilities(
            provider=ProviderType.KIMI,
            model_name="kimi-k2-0711-preview",
            friendly_name="Kimi K2 Thinking",
            context_window=131_072,
            max_output_tokens=100_000,
            supports_extended_thinking=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.3),
            description="K2 (0711 preview) with enhanced reasoning profile",
            aliases=["kimi-thinking-preview"],
        ),
    }

    def __init__(self, api_key: str, **kwargs):
        """Initialize Kimi provider with Moonshot AI API configuration.

        Args:
            api_key: Moonshot AI API key
            **kwargs: Additional configuration passed to parent class
        """
        # Set Moonshot AI API endpoint
        kwargs.setdefault("base_url", "https://api.moonshot.ai/v1")
        super().__init__(api_key, **kwargs)
        logger.info("Initialized Kimi provider with Moonshot AI API")

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific Kimi model.

        Args:
            model_name: Name of the model (can be alias)

        Returns:
            ModelCapabilities object for the model

        Raises:
            ValueError: If model is not supported or not allowed by restrictions
        """
        resolved_name = self._resolve_model_name(model_name)

        if resolved_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported Kimi model: {model_name}")

        # Apply model restrictions if configured
        from utils.model_restrictions import get_restriction_service
        restriction_service = get_restriction_service()
        if not restriction_service.is_allowed(ProviderType.KIMI, resolved_name, model_name):
            raise ValueError(f"Kimi model '{model_name}' is not allowed by current restrictions.")

        return self.SUPPORTED_MODELS[resolved_name]

    def get_provider_type(self) -> ProviderType:
        """Get the provider type for this provider.

        Returns:
            ProviderType.KIMI
        """
        return ProviderType.KIMI

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
        """Generate content using Kimi models.

        Args:
            prompt: Input prompt text
            model_name: Name of the model to use (can be alias)
            **kwargs: Additional generation parameters

        Returns:
            ModelResponse with generated content and metadata
        """
        # Resolve the provided name (which may be an alias) to the provider's base key
        resolved_key = self._resolve_model_name(model_name)

        # Pure chat.completions.create; web tools removed; use only core params
        # Fall back to the resolved key if we cannot find a capabilities entry (defensive)
        canonical_model = resolved_key
        try:
            caps = self.SUPPORTED_MODELS.get(resolved_key)
            if caps and isinstance(caps, ModelCapabilities):
                canonical_model = caps.model_name or resolved_key
        except Exception:
            # Keep canonical_model as resolved_key on any unexpected issue
            pass

        # Delegate to the OpenAI-compatible implementation using the canonical provider model name
        return super().generate_content(prompt=prompt, model_name=canonical_model, **kwargs)

    def upload_file(self, file_path: str, purpose: str = "file-extract") -> str:
        """Upload a local file to Moonshot (Kimi) and return file_id.

        Follows Moonshot's Files API semantics. Default purpose is 'file-extract',
        which triggers provider-side parsing and makes the extracted text retrievable
        via client.files.content(file_id=...).text

        Args:
            file_path: Absolute or relative path to the file on disk
            purpose: Provider-specific purpose tag (default 'file-extract')

        Returns:
            The provider file_id string
        """
        try:
            from pathlib import Path
            p = Path(file_path)
            if not p.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            # OpenAI-compatible clients support files.create(file=..., purpose=...)
            result = self.client.files.create(file=p, purpose=purpose)
            file_id = getattr(result, "id", None) or (result.get("id") if isinstance(result, dict) else None)
            if not file_id:
                raise RuntimeError("Moonshot upload did not return a file id")
            return file_id
        except Exception as e:
            logger.error(f"Kimi file upload failed for {file_path}: {e}")
            raise

    def fetch_file_content(self, file_id: str) -> str:
        """Retrieve parsed text content for a previously uploaded file.

        Args:
            file_id: Provider file id returned by upload_file

        Returns:
            Extracted text content
        """
        try:
            # Moonshot recommends .content().text in latest SDK
            return self.client.files.content(file_id=file_id).text
        except Exception as e:
            logger.error(f"Kimi fetch_file_content failed for {file_id}: {e}")
            raise

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
        """List all available Kimi models.

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
            if restriction_service.is_allowed(ProviderType.KIMI, model_name):
                allowed_models.append(model_name)
                # Add aliases for allowed models
                for alias in capabilities.aliases:
                    if restriction_service.is_allowed(ProviderType.KIMI, model_name, alias):
                        allowed_models.append(alias)

        return allowed_models


