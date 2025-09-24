import sys
sys.path.append(".")
from src.providers.registry import ModelProviderRegistry
from utils.model_restrictions import apply_model_restrictions

"""
Provider Configuration Module

This module handles the configuration and initialization of AI model providers
for the EX MCP Server. It manages API keys, model restrictions, and provider
registry setup.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

def configure_providers():
    """
    Configure and validate AI providers based on available API keys.

    This function checks for API keys and registers the appropriate providers.
    At least one valid API key (Kimi or GLM) is required.

    Raises:
        ValueError: If no valid API keys are found or conflicting configurations detected
    """
    # Log environment variable status for debugging
    logger.debug("Checking environment variables for API keys...")
    api_keys_to_check = ["KIMI_API_KEY", "GLM_API_KEY", "OPENROUTER_API_KEY", "CUSTOM_API_URL"]
    for key in api_keys_to_check:
        value = os.getenv(key)
        logger.debug(f"  {key}: {'[PRESENT]' if value else '[MISSING]'}")

    # Optional explicit provider gating (comma-separated names matching ProviderType)
    disabled_providers = {p.strip().upper() for p in os.getenv("DISABLED_PROVIDERS", "").split(",") if p.strip()}
    allowed_providers = {p.strip().upper() for p in os.getenv("ALLOWED_PROVIDERS", "").split(",") if p.strip()}

    from src.providers import ModelProviderRegistry
    from src.providers.base import ProviderType
    from src.providers.custom import CustomProvider
    from utils.model_restrictions import get_restriction_service

    # Import provider classes lazily to avoid optional dependency import errors
    OpenAIModelProvider = None
    GeminiModelProvider = None
    XAIModelProvider = None
    KimiModelProvider = None
    GLMModelProvider = None
    OpenRouterProvider = None
    DIALModelProvider = None

    # Force-disable providers we don't support in this deployment
    disabled_providers.update({"GOOGLE", "OPENAI", "XAI", "DIAL"})

    valid_providers = []
    has_native_apis = False
    has_openrouter = False
    has_custom = False

    # Gemini disabled by policy
    gemini_key = os.getenv("GEMINI_API_KEY")

    # OpenAI disabled by policy
    openai_key = os.getenv("OPENAI_API_KEY")
    logger.debug(f"OpenAI key check: key={'[PRESENT]' if openai_key else '[MISSING]'}")

    # X.AI disabled by policy
    xai_key = os.getenv("XAI_API_KEY")

    # DIAL disabled by policy
    dial_key = os.getenv("DIAL_API_KEY")

    # Check for Kimi API key (accept vendor alias)
    kimi_key = os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY")
    if kimi_key and kimi_key != "your_kimi_api_key_here" and "KIMI" not in disabled_providers and (not allowed_providers or "KIMI" in allowed_providers):
        try:
            from src.providers.kimi import KimiModelProvider as _Kimi
            KimiModelProvider = _Kimi  # type: ignore
            valid_providers.append("Kimi")
            has_native_apis = True
            logger.info("Kimi API key found - Moonshot AI models available")
        except Exception:
            logger.warning("Kimi provider import failed; continuing without Kimi")

    # Check for GLM API key (accept vendor alias)
    glm_key = os.getenv("GLM_API_KEY") or os.getenv("ZHIPUAI_API_KEY")
    if glm_key and glm_key != "your_glm_api_key_here" and "GLM" not in disabled_providers and (not allowed_providers or "GLM" in allowed_providers):
        try:
            from src.providers.glm import GLMModelProvider as _GLM
            GLMModelProvider = _GLM  # type: ignore
            valid_providers.append("GLM")
            has_native_apis = True
            logger.info("GLM API key found - ZhipuAI models available")
        except Exception:
            logger.warning("GLM provider import failed; continuing without GLM")

    # Check for OpenRouter API key
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    logger.debug(f"OpenRouter key check: key={'[PRESENT]' if openrouter_key else '[MISSING]'}")
    if openrouter_key and openrouter_key != "your_openrouter_api_key_here":
        valid_providers.append("OpenRouter")
        has_openrouter = True
        logger.info("OpenRouter API key found - Multiple models available via OpenRouter")
    else:
        if not openrouter_key:
            logger.debug("OpenRouter API key not found in environment")
        else:
            logger.debug("OpenRouter API key is placeholder value")

    # Check for custom API endpoint (Ollama, vLLM, etc.)
    custom_url = os.getenv("CUSTOM_API_URL")
    if custom_url:
        # IMPORTANT: Always read CUSTOM_API_KEY even if empty
        # - Some providers (vLLM, LM Studio, enterprise APIs) require authentication
        # - Others (Ollama) work without authentication (empty key)
        # - DO NOT remove this variable - it's needed for provider factory function
        custom_key = os.getenv("CUSTOM_API_KEY", "")  # Default to empty (Ollama doesn't need auth)
        custom_model = os.getenv("CUSTOM_MODEL_NAME", "llama3.2")
        valid_providers.append(f"Custom API ({custom_url})")
        has_custom = True
        logger.info(f"Custom API endpoint found: {custom_url} with model {custom_model}")
        if custom_key:
            logger.debug("Custom API key provided for authentication")
        else:
            logger.debug("No custom API key provided (using unauthenticated access)")

    # Register providers in priority order:
    # 1. Native APIs first (most direct and efficient)
    if has_native_apis:
        if kimi_key and kimi_key != "your_kimi_api_key_here" and "KIMI" not in disabled_providers:
            ModelProviderRegistry.register_provider(ProviderType.KIMI, KimiModelProvider)
        if glm_key and glm_key != "your_glm_api_key_here" and "GLM" not in disabled_providers:
            ModelProviderRegistry.register_provider(ProviderType.GLM, GLMModelProvider)

    # 2. Custom provider second (for local/private models)
    if has_custom and "CUSTOM" not in disabled_providers:
        # Factory function that creates CustomProvider with proper parameters
        def custom_provider_factory(api_key=None):
            # api_key is CUSTOM_API_KEY (can be empty for Ollama), base_url from CUSTOM_API_URL
            base_url = os.getenv("CUSTOM_API_URL", "")
            return CustomProvider(api_key=api_key or "", base_url=base_url)  # Use provided API key or empty string

        ModelProviderRegistry.register_provider(ProviderType.CUSTOM, custom_provider_factory)

    # 3. OpenRouter last (catch-all for everything else)
    if has_openrouter and "OPENROUTER" not in disabled_providers:
        ModelProviderRegistry.register_provider(ProviderType.OPENROUTER, OpenRouterProvider)

    # Require at least one valid provider
    if not valid_providers:
        raise ValueError(
            "At least one API configuration is required. Please set either:\n"
            "- KIMI_API_KEY for Moonshot Kimi models\n"
            "- GLM_API_KEY for ZhipuAI GLM models\n"
            "- OPENROUTER_API_KEY for OpenRouter (multiple models)\n"
            "- CUSTOM_API_URL for local models (Ollama, vLLM, etc.)"
        )

    logger.info(f"Available providers: {', '.join(valid_providers)}")
    # Diagnostic: summarize configured providers and model counts for quick visibility
    try:
        with_keys = [p.name for p in ModelProviderRegistry.get_available_providers_with_keys()]
        glm_models = ModelProviderRegistry.get_available_model_names(provider_type=ProviderType.GLM)
        kimi_models = ModelProviderRegistry.get_available_model_names(provider_type=ProviderType.KIMI)
        logger.info(
            "Providers configured: %s; GLM models: %d; Kimi models: %d",
            ", ".join(with_keys) if with_keys else "none",
            len(glm_models),
            len(kimi_models),
        )
    except Exception as _e:
        logger.debug(f"Provider availability summary skipped: {_e}")


    # Log provider priority
    priority_info = []
    if has_native_apis:
        priority_info.append("Native APIs (Gemini, OpenAI)")
    if has_custom:
        priority_info.append("Custom endpoints")
    if has_openrouter:
        priority_info.append("OpenRouter (catch-all)")

    if len(priority_info) > 1:
        logger.info(f"Provider priority: {' â†’ '.join(priority_info)}")

    # Register cleanup function for providers
    def cleanup_providers():
        """Clean up all registered providers on shutdown."""
        try:
            registry = ModelProviderRegistry()
            if hasattr(registry, "_initialized_providers"):
                for provider in list(registry._initialized_providers.items()):
                    try:
                        if provider and hasattr(provider, "close"):
                            provider.close()
                    except Exception:
                        # Logger might be closed during shutdown
                        pass
        except Exception:
            # Silently ignore any errors during cleanup
            pass

    atexit.register(cleanup_providers)

    # Check and log model restrictions
    restriction_service = get_restriction_service()
    restrictions = restriction_service.get_restriction_summary()

    if restrictions:
        logger.info("Model restrictions configured:")
        for provider_name, allowed_models in restrictions.items():
            if isinstance(allowed_models, list):
                logger.info(f"  {provider_name}: {', '.join(allowed_models)}")
            else:
                logger.info(f"  {provider_name}: {allowed_models}")

        # Validate restrictions against known models
        provider_instances = {}
        provider_types_to_validate = [
            ProviderType.KIMI,
            ProviderType.GLM,
            ProviderType.CUSTOM,
            ProviderType.OPENROUTER,
        ]
        for provider_type in provider_types_to_validate:
            provider = ModelProviderRegistry.get_provider(provider_type)
            if provider:
                provider_instances[provider_type] = provider

        if provider_instances:
            restriction_service.validate_against_known_models(provider_instances)
    else:
        logger.info("No model restrictions configured - all models allowed")

    # Check if auto mode has any models available after restrictions
    from config import IS_AUTO_MODE

    if IS_AUTO_MODE:
        available_models = ModelProviderRegistry.get_available_models(respect_restrictions=True)
        if not available_models:
            logger.error(
                "Auto mode is enabled but no models are available after applying restrictions. "
                "Please check your OPENAI_ALLOWED_MODELS and GOOGLE_ALLOWED_MODELS settings."
            )
            raise ValueError(
                "No models available for auto mode due to restrictions. "
                "Please adjust your allowed model settings or disable auto mode."
            )


@server.list_tools()
