"""Model provider registry for managing available providers."""

import logging
import os
import threading
from typing import Any, Optional, TYPE_CHECKING

# Ensure environment variables from project .env are available even when server.py
# is not the entrypoint (e.g., direct tool/EX-AI invocations)
try:
    from pathlib import Path
    from dotenv import load_dotenv  # type: ignore
    # Compute repository root (three levels up from this file: src/providers/registry.py)
    repo_root = Path(__file__).resolve().parents[2]
    env_path = repo_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=str(env_path))
    else:
        logging.warning(".env file not found at %s", env_path)
except Exception as e:
    # If dotenv is not installed or any error occurs, proceed with system env only
    logging.warning("dotenv load failed: %s; proceeding with system environment only", e)

from .base import ModelProvider, ProviderType

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from utils.health import HealthManager, CircuitState  # self-healing integration
import asyncio
import time

# Feature flags (env-driven)
_DEF = lambda k, d: os.getenv(k, d).lower()

def _health_enabled() -> bool:
    return _DEF("HEALTH_CHECKS_ENABLED", "false") == "true"

def _cb_enabled() -> bool:
    return _DEF("CIRCUIT_BREAKER_ENABLED", "false") == "true"

def _health_log_only() -> bool:
    return _DEF("HEALTH_LOG_ONLY", "true") == "true"

def _retry_attempts() -> int:
    try:
        return int(os.getenv("RETRY_ATTEMPTS", "2"))
    except Exception:
        return 2

def _backoff_base() -> float:
    try:
        return float(os.getenv("RETRY_BACKOFF_BASE", "0.5"))
    except Exception:
        return 0.5

def _backoff_max() -> float:
    try:
        return float(os.getenv("RETRY_BACKOFF_MAX", "4.0"))
    except Exception:
        return 4.0
def _free_tier_enabled() -> bool:
    return os.getenv("FREE_TIER_PREFERENCE_ENABLED", "false").lower() == "true"

def _free_model_list() -> set[str]:
    raw = os.getenv("FREE_MODEL_LIST", "")
    return set([m.strip().lower() for m in raw.split(",") if m.strip()])

def _apply_free_first(models: list[str]) -> list[str]:
    if not _free_tier_enabled():
        return models
    free = _free_model_list()
    if not free:
        return models
    free_models = [m for m in models if m.lower() in free]
    paid_models = [m for m in models if m.lower() not in free]
    return free_models + paid_models

def _cost_aware_enabled() -> bool:
    return os.getenv("COST_AWARE_ROUTING_ENABLED", "false").lower() == "true"

def _load_model_costs() -> dict[str, float]:
    import json
    raw = os.getenv("MODEL_COSTS_JSON", "{}")
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {str(k): float(v) for k, v in data.items()}
    except Exception:
        pass
    return {}

def _max_cost_per_request() -> float | None:
    try:
        val = os.getenv("MAX_COST_PER_REQUEST")
        return float(val) if val else None
    except Exception:
        return None

def _apply_cost_aware(models: list[str], tool_category) -> list[str]:
    if not _cost_aware_enabled():
        return models
    costs = _load_model_costs()
    if not costs:
        return models
    max_cost = _max_cost_per_request()
    # Filter and sort by configured cost if present; unknown costs retain original order at end
    def model_key(m: str):
        return (0, costs[m]) if m in costs else (1, float('inf'))
    filtered = [m for m in models if (max_cost is None or (m in costs and costs[m] <= max_cost)) or (m not in costs)]
    filtered.sort(key=model_key)
    return filtered


_HEALTH_MANAGER: HealthManager | None = None

def _get_health_manager() -> HealthManager:
    global _HEALTH_MANAGER
    if _HEALTH_MANAGER is None:
        _HEALTH_MANAGER = HealthManager()
    return _HEALTH_MANAGER

class HealthWrappedProvider(ModelProvider):
    """Wrapper that records provider health and applies simple retry/backoff.
    Only active when HEALTH_CHECKS_ENABLED=true. Selection gating happens in registry.
    """
    def __init__(self, inner: ModelProvider):
        self._inner = inner
        self._ptype = inner.get_provider_type()
        self._health = _get_health_manager().get(self._ptype.value)

    # Pass-throughs to satisfy abstract interface
    def get_provider_type(self) -> ProviderType:
        return self._ptype


    # Ensure restriction validation sees real model lists/capabilities
    def get_model_configurations(self) -> dict[str, Any]:
        return self._inner.get_model_configurations()

    def get_all_model_aliases(self) -> dict[str, list[str]]:
        return self._inner.get_all_model_aliases()



    def list_all_known_models(self) -> list[str]:
        return self._inner.list_all_known_models()

    def get_preferred_model(self, category: "ToolModelCategory", allowed_models: list[str]) -> str | None:
        # Delegate if inner provider implements preference; else no preference
        try:
            return self._inner.get_preferred_model(category, allowed_models)  # type: ignore[attr-defined]
        except Exception:
            return None

    # Legacy compatibility: alias to inner when callers expect raw provider type
    def get_provider_type_raw(self):
        return self._inner.get_provider_type()

    @staticmethod
    def _schedule(coro) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except Exception:
            # If no loop or running in a threadpool, skip recording instead of crashing
            pass

    # Forwarding methods
    def get_capabilities(self, model_name: str):
        return self._inner.get_capabilities(model_name)

    def validate_model_name(self, model_name: str) -> bool:
        return self._inner.validate_model_name(model_name)

    def list_models(self, respect_restrictions: bool = True):
        fn = getattr(self._inner, "list_models", None)
        if callable(fn):
            return fn(respect_restrictions=respect_restrictions)
        raise NotImplementedError

    def supports_thinking_mode(self, model_name: str) -> bool:
        fn = getattr(self._inner, "supports_thinking_mode", None)
        if callable(fn):
            try:
                return bool(fn(model_name))
            except Exception:
                return False
        return False

    def count_tokens(self, text: str, model_name: str) -> int:
        # Token count is fast; treat errors as failure but no retries
        try:
            val = self._inner.count_tokens(text, model_name)
            if _health_enabled() and not _health_log_only():
                HealthWrappedProvider._schedule(self._health.record_result(True))
            return val
        except Exception:
            if _health_enabled():
                # log-only still records but does not gate selection here
                HealthWrappedProvider._schedule(self._health.record_result(False))
            raise

    def generate_content(self, prompt: str, model_name: str, system_prompt: str | None = None, temperature: float = 0.3, max_output_tokens: int | None = None, **kwargs):
        attempts = max(1, _retry_attempts())
        delay = _backoff_base()
        last_exc = None
        for i in range(attempts):
            try:
                t0 = time.perf_counter()
                result = self._inner.generate_content(
                    prompt=prompt,
                    model_name=model_name,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    **kwargs,
                )
                latency_ms = (time.perf_counter() - t0) * 1000.0
                if _health_enabled() and not _health_log_only():
                    HealthWrappedProvider._schedule(self._health.record_result(True))
                try:
                    from utils.metrics import record_provider_call
                    record_provider_call(self._ptype.value, model_name, True, latency_ms)
                except Exception:
                    pass
                return result
            except Exception as e:
                last_exc = e
                if _health_enabled():
                    HealthWrappedProvider._schedule(self._health.record_result(False))
                try:
                    from utils.metrics import record_provider_call
                    record_provider_call(self._ptype.value, model_name, False, None)
                except Exception:
                    pass
                # Simple backoff before retrying
                if i < attempts - 1:
                    time.sleep(min(delay, _backoff_max()))
                    delay *= 2
        # Exceeded retries
        raise last_exc


class ModelProviderRegistry:
    """Registry for managing model providers."""

    _instance = None
    # In-memory telemetry (lightweight). Structure:
    # telemetry = {
    #   "model_name": {"success": int, "failure": int, "latency_ms": [..], "input_tokens": int, "output_tokens": int}
    # }
    _telemetry: dict[str, dict[str, Any]] = {}
    _telemetry_lock = threading.RLock()

    # Provider priority order for model selection
    # Native APIs first (prioritize Kimi/GLM per project usage), then custom endpoints, then catch-all providers
    PROVIDER_PRIORITY_ORDER = [
        ProviderType.KIMI,   # Direct Kimi/Moonshot access (preferred)
        ProviderType.GLM,    # Direct GLM/ZhipuAI access (preferred)
        ProviderType.CUSTOM, # Local/self-hosted models
        ProviderType.OPENROUTER,  # Catch-all for cloud models (optional)
    ]

    def __new__(cls):
        """Singleton pattern for registry."""
        if cls._instance is None:
            logging.debug("REGISTRY: Creating new registry instance")
            cls._instance = super().__new__(cls)
            # Initialize instance dictionaries on first creation
            cls._instance._providers = {}
            cls._instance._initialized_providers = {}
            # Cache: model_name -> ProviderType | None (explicit negative caching)
            cls._instance._model_provider_cache = {}
            logging.debug(f"REGISTRY: Created instance {cls._instance}")
        return cls._instance

    @classmethod
    def register_provider(cls, provider_type: ProviderType, provider_class: type[ModelProvider]) -> None:
        """Register a new provider class.

        Args:
            provider_type: Type of the provider (e.g., ProviderType.GOOGLE)
            provider_class: Class that implements ModelProvider interface
        """
        instance = cls()
        instance._providers[provider_type] = provider_class

    @classmethod
    def get_provider(cls, provider_type: ProviderType, force_new: bool = False) -> Optional[ModelProvider]:
        """Get an initialized provider instance.

        Args:
            provider_type: Type of provider to get
            force_new: Force creation of new instance instead of using cached

        Returns:
            Initialized ModelProvider instance or None if not available
        """
        instance = cls()

        # Enforce allowlist if configured (security hardening)
        allowed = os.getenv("ALLOWED_PROVIDERS", "").strip()
        if allowed:
            allow = {p.strip().upper() for p in allowed.split(",") if p.strip()}
            if provider_type.name not in allow:
                logging.debug("Provider %s skipped by ALLOWED_PROVIDERS", provider_type.name)
                return None

        # Return cached instance if available and not forcing new
        if not force_new and provider_type in instance._initialized_providers:
            return instance._initialized_providers[provider_type]

        # Check if provider class is registered
        if provider_type not in instance._providers:
            return None

        # Get API key from environment
        api_key = cls._get_api_key_for_provider(provider_type)

        # Get provider class or factory function
        provider_class = instance._providers[provider_type]

        # Defensive: transient init protection
        try:
            # For custom providers, handle special initialization requirements
            if provider_type == ProviderType.CUSTOM:
                # Check if it's a factory function (callable but not a class)
                if callable(provider_class) and not isinstance(provider_class, type):
                    # Factory function - call it with api_key parameter
                    provider = provider_class(api_key=api_key)
                else:
                    # Regular class - need to handle URL requirement
                    custom_url = os.getenv("CUSTOM_API_URL", "")
                    if not custom_url:
                        if api_key:  # Key is set but URL is missing
                            logging.warning("CUSTOM_API_KEY set but CUSTOM_API_URL missing – skipping Custom provider")
                        return None
                    # Use empty string as API key for custom providers that don't need auth (e.g., Ollama)
                    # This allows the provider to be created even without CUSTOM_API_KEY being set
                    api_key = api_key or ""
                    # Initialize custom provider with both API key and base URL
                    provider = provider_class(api_key=api_key, base_url=custom_url)
            else:
                if not api_key:
                    return None
                # Initialize non-custom provider with API key and optional base_url from env for specific providers
                if provider_type in (ProviderType.KIMI, ProviderType.GLM):
                    # Support canonical and vendor-specific environment variable names
                    # KIMI: prefer KIMI_API_URL, fallback to MOONSHOT_API_URL
                    # GLM:  prefer GLM_API_URL,  fallback to ZHIPUAI_API_URL
                    if provider_type == ProviderType.KIMI:
                        base_url = os.getenv("KIMI_API_URL") or os.getenv("MOONSHOT_API_URL")
                    else:
                        base_url = os.getenv("GLM_API_URL") or os.getenv("ZHIPUAI_API_URL")
                    if base_url:
                        provider = provider_class(api_key=api_key, base_url=base_url)
                    else:
                        provider = provider_class(api_key=api_key)
                else:
                    provider = provider_class(api_key=api_key)
        except Exception as e:
            # Failed to create provider (transient or misconfig). Do not raise here.
            logging.warning("Provider %s initialization failed: %s", provider_type, e)
            return None

        # Wrap with health if enabled
        if _health_enabled():
            provider = HealthWrappedProvider(provider)

        # Cache the instance
        instance._initialized_providers[provider_type] = provider

        return provider

    @classmethod
    def get_provider_for_model(cls, model_name: str) -> Optional[ModelProvider]:
        """Get provider instance for a specific model name with memoization.

        Provider priority order:
        1. Native APIs (KIMI, GLM) - Most direct and efficient in this project
        2. CUSTOM - For local/private models with specific endpoints
        3. OPENROUTER - Catch-all for cloud models via unified API
        """
        logging.debug(f"get_provider_for_model called with model_name='{model_name}'")

        # Normalize cache key
        instance = cls()
        cache_key = (model_name or "").strip().lower()
        cache = getattr(instance, "_model_provider_cache", None)
        if isinstance(cache, dict) and cache_key in cache:
            cached_ptype = cache[cache_key]
            if cached_ptype is None:
                logging.debug(f"Cache negative-hit for model {model_name}")
                return None
            prov = cls.get_provider(cached_ptype)
            if prov:
                logging.debug(f"Cache hit for model {model_name}: {cached_ptype}")
                return prov
            # Fall through if provider instance could not be created

        logging.debug(f"Registry instance: {instance}")
        logging.debug(f"Available providers in registry: {list(instance._providers.keys())}")

        found_ptype: ProviderType | None = None
        for provider_type in cls.PROVIDER_PRIORITY_ORDER:
            if provider_type in instance._providers:
                logging.debug(f"Found {provider_type} in registry")

                # Health gating: skip if circuit is OPEN (only when enabled and not log-only)
                if _health_enabled() and _cb_enabled():
                    health = _get_health_manager().get(provider_type.value)
                    if health.breaker.state == CircuitState.OPEN:
                        logging.warning("Skipping provider %s due to OPEN circuit", provider_type)
                        continue

                # Get or create provider instance
                provider = cls.get_provider(provider_type)
                if provider and provider.validate_model_name(model_name):
                    logging.debug(f"{provider_type} validates model {model_name}")
                    found_ptype = provider_type
                    break
                else:
                    logging.debug(f"{provider_type} does not validate model {model_name}")
            else:
                logging.debug(f"{provider_type} not found in registry")

        # Update cache and return
        if isinstance(cache, dict):
            cache[cache_key] = found_ptype  # store None for negative cache
        if found_ptype is None:
            logging.debug(f"No provider found for model {model_name}")
            return None
        return cls.get_provider(found_ptype)

    @classmethod
    def get_available_providers(cls) -> list[ProviderType]:
        """Get list of registered provider types."""
        instance = cls()
        providers = list(instance._providers.keys())
        allowed = os.getenv("ALLOWED_PROVIDERS", "").strip()
        if allowed:
            allow = {p.strip().upper() for p in allowed.split(",") if p.strip()}
            providers = [p for p in providers if p.name in allow]
        return providers

    @classmethod
    def get_available_models(cls, respect_restrictions: bool = True) -> dict[str, ProviderType]:
        """Get mapping of all available models to their providers.

        Args:
            respect_restrictions: If True, filter out models not allowed by restrictions

        Returns:
            Dict mapping model names to provider types
        """
        # Import here to avoid circular imports
        from utils.model_restrictions import get_restriction_service

        restriction_service = get_restriction_service() if respect_restrictions else None
        models: dict[str, ProviderType] = {}
        instance = cls()

        for provider_type in instance._providers:
            provider = cls.get_provider(provider_type)
            if not provider:
                continue

            try:
                available = provider.list_models(respect_restrictions=respect_restrictions)
            except NotImplementedError:
                logging.warning("Provider %s does not implement list_models", provider_type)
                continue

            for model_name in available:
                # =====================================================================================
                # CRITICAL: Prevent double restriction filtering (Fixed Issue #98)
                # =====================================================================================
                # Previously, both the provider AND registry applied restrictions, causing
                # double-filtering that resulted in "no models available" errors.
                #
                # Logic: If respect_restrictions=True, provider already filtered models,
                # so registry should NOT filter them again.
                # TEST COVERAGE: tests/test_provider_routing_bugs.py::TestOpenRouterAliasRestrictions
                # =====================================================================================
                if (
                    restriction_service
                    and not respect_restrictions  # Only filter if provider didn't already filter
                    and not restriction_service.is_allowed(provider_type, model_name)
                ):
                    logging.debug("Model %s filtered by restrictions", model_name)
                    continue
                models[model_name] = provider_type

        return models

    @classmethod
    def get_available_model_names(cls, provider_type: Optional[ProviderType] = None) -> list[str]:
        """Get list of available model names, optionally filtered by provider.

        This respects model restrictions automatically.

        Args:
            provider_type: Optional provider to filter by

        Returns:
            List of available model names
        """
        available_models = cls.get_available_models(respect_restrictions=True)

        if provider_type:
            # Filter by specific provider
            return [name for name, ptype in available_models.items() if ptype == provider_type]
        else:
            # Return all available models
            return list(available_models.keys())

    @classmethod
    def list_available_models(cls, provider_type: Optional[ProviderType] = None) -> list[str]:
        """Alias maintained for backward compatibility with server.py.
        Returns list of available model names, optionally filtered by provider.
        """
        return cls.get_available_model_names(provider_type=provider_type)

    @classmethod
    def get_available_providers_with_keys(cls) -> list[ProviderType]:
        """Return providers that can be initialized with current env keys.
        Used by server diagnostics. Does not throw on init errors.
        """
        instance = cls()
        result: list[ProviderType] = []
        for ptype in list(instance._providers.keys()):
            try:
                if cls.get_provider(ptype) is not None:
                    result.append(ptype)
            except Exception:
                # Be permissive for diagnostics
                continue
        return result

    @classmethod
    def get_preferred_fallback_model(cls, tool_category: Optional["ToolModelCategory"] = None) -> str:
        """Select a reasonable fallback model across providers.

        Strategy:
        1) For each provider in priority order, get allowed models
        2) Apply cost-aware + free-tier ordering
        3) Ask provider for preference; else take first allowed
        4) If nothing available, default to a safe GLM/Kimi model present in stack
        """
        try:
            from tools.models import ToolModelCategory as _Cat
        except Exception:
            class _Cat:  # minimal stub
                FAST_RESPONSE = object()
                EXTENDED_REASONING = object()
                BALANCED = object()
        effective_cat = tool_category or getattr(_Cat, "BALANCED")

        first_available: Optional[str] = None

        for ptype in cls.PROVIDER_PRIORITY_ORDER:
            prov = cls.get_provider(ptype)
            if not prov:
                continue
            try:
                allowed = cls._get_allowed_models_for_provider(prov, ptype)  # type: ignore[attr-defined]
            except Exception:
                # Fallback to provider list when helper is not available
                try:
                    allowed = prov.list_models(respect_restrictions=True)
                except Exception:
                    allowed = []
            if not allowed:
                continue
            # Track first available
            if not first_available:
                first_available = sorted(allowed)[0]
            # Intra-provider ordering
            ordered = _apply_free_first(_apply_cost_aware(list(allowed), effective_cat))
            # Ask provider for preference
            try:
                chosen = prov.get_preferred_model(effective_cat, ordered)  # type: ignore[attr-defined]
            except Exception:
                chosen = None
            if chosen:
                return chosen
            # Otherwise pick first ordered
            if ordered:
                return ordered[0]

        # Cross-provider default if nothing chosen
        try:
            if cls.get_provider(ProviderType.GLM):
                return "glm-4.5-flash"
            if cls.get_provider(ProviderType.KIMI):
                return "kimi-k2-0711-preview"
        except Exception:
            pass
        return os.getenv("DEFAULT_MODEL", "glm-4.5-flash") or "glm-4.5-flash"


    @classmethod
    def get_kimi_provider(cls) -> Optional[ModelProvider]:
        """Helper to get Kimi provider with graceful fallback to GLM if configured.

        Fallback sequence:
        1) KIMI (if initialized)
        2) If Kimi unavailable, return None here; routing code should fallback to GLM/DEFAULT_MODEL
        """
        kimi_provider = cls.get_provider(ProviderType.KIMI)
        if kimi_provider:
            return kimi_provider
        return None

    @classmethod
    def get_glm_provider(cls) -> Optional[ModelProvider]:
        """Helper to get GLM provider."""
        return cls.get_provider(ProviderType.GLM)

    @classmethod
    def get_best_provider_for_category(cls, category: "ToolModelCategory", allowed_models: list[str]) -> Optional[tuple[ModelProvider, str]]:
        """Select best provider and model for a functional category.

        This implements environment preferences and cost-aware routing.
        """
        # 1) Aggregate allowed by provider while preserving priority order
        available = cls.get_available_models(respect_restrictions=True)
        by_provider: dict[ProviderType, list[str]] = {}
        for name, ptype in available.items():
            if name in allowed_models:
                by_provider.setdefault(ptype, []).append(name)

        # Apply free-tier preference then cost-aware ordering within each provider
        for ptype, names in list(by_provider.items()):
            names = _apply_free_first(names)
            names = _apply_cost_aware(names, category)
            by_provider[ptype] = names

        # 2) Provider priority selection
        for ptype in cls.PROVIDER_PRIORITY_ORDER:
            if ptype not in by_provider or not by_provider[ptype]:
                continue
            provider = cls.get_provider(ptype)
            if not provider:
                continue

            # Provider-specific preference env var
            preferred = provider.get_preferred_model(category, by_provider[ptype])
            chosen = preferred or (by_provider[ptype][0] if by_provider[ptype] else None)
            if chosen:
                return provider, chosen

        return None

    @staticmethod
    def _get_api_key_for_provider(provider_type: ProviderType) -> Optional[str]:
        """Get API key for provider from environment variables.

        Supports both canonical and vendor-specific names to reduce friction.
        Example:
        - KIMI: KIMI_API_KEY or MOONSHOT_API_KEY
        - GLM:  GLM_API_KEY  or ZHIPUAI_API_KEY
        """
        try:
            mapping: dict[ProviderType, list[str]] = {
                ProviderType.GOOGLE: ["GOOGLE_API_KEY"],
                ProviderType.OPENAI: ["OPENAI_API_KEY"],
                ProviderType.XAI: ["XAI_API_KEY"],
                ProviderType.OPENROUTER: ["OPENROUTER_API_KEY"],
                ProviderType.CUSTOM: ["CUSTOM_API_KEY"],
                ProviderType.DIAL: ["DIAL_API_KEY"],
                ProviderType.KIMI: ["KIMI_API_KEY", "MOONSHOT_API_KEY"],
                ProviderType.GLM: ["GLM_API_KEY", "ZHIPUAI_API_KEY"],
            }

            for var in mapping.get(provider_type, []):
                val = os.getenv(var)
                if val:
                    return val
            return None
        except Exception as e:
            logging.warning("Error getting API key for provider %s: %s", provider_type, e)
            return None

    @classmethod
    def record_telemetry(
        cls,
        model_name: str,
        success: bool,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float | None = None,
    ) -> None:
        """Record telemetry for a model call."""
        with cls._telemetry_lock:
            rec = cls._telemetry.setdefault(model_name, {"success": 0, "failure": 0, "latency_ms": [], "input_tokens": 0, "output_tokens": 0})
            if success:
                rec["success"] += 1
            else:
                rec["failure"] += 1
            rec["input_tokens"] += max(0, input_tokens)
            rec["output_tokens"] += max(0, output_tokens)
            if latency_ms is not None:
                rec["latency_ms"].append(float(latency_ms))
        # Best-effort JSONL observability for token usage
        try:
            from utils.observability import record_token_usage
            provider = "unknown"
            try:
                prov = cls.get_provider_for_model(model_name)
                if prov:
                    ptype = prov.get_provider_type()
                    provider = getattr(ptype, "value", getattr(ptype, "name", "unknown"))
            except Exception:
                provider = "unknown"
            if input_tokens or output_tokens:
                record_token_usage(str(provider), model_name, int(input_tokens), int(output_tokens))
        except Exception:
            pass


    @classmethod
    def _get_allowed_models_for_provider(cls, provider: ModelProvider, provider_type: ProviderType) -> list[str]:
        """Return canonical model names supported by a provider after restriction filtering.
        Uses provider.list_models(respect_restrictions=False) when available, otherwise
        falls back to the provider's SUPPORTED_MODELS keys.
        """
        try:
            from utils.model_restrictions import get_restriction_service
        except Exception:
            get_restriction_service = None  # type: ignore

        restriction_service = get_restriction_service() if get_restriction_service else None

        # Gather supported models without double-filtering
        try:
            supported = provider.list_models(respect_restrictions=False)
        except (NotImplementedError, AttributeError):
            try:
                supported = list(getattr(provider, "SUPPORTED_MODELS", {}).keys())
            except Exception:
                supported = []

        allowed: list[str] = []
        for name in supported:
            try:
                if restriction_service is None or restriction_service.is_allowed(provider_type, name, name):
                    allowed.append(name)
            except Exception:
                # Be permissive under diagnostics/transient failures
                allowed.append(name)
        return allowed

    @classmethod
    def _auggie_fallback_chain(
        cls,
        category: Optional["ToolModelCategory"],
        hints: Optional[list[str]] = None,
    ) -> list[str]:
        """Return a prioritized list of candidate models for a category.
        Priority sources:
          1) auggie.config 'fallback' chains (if configured)
          2) Seed with get_preferred_fallback_model, then expand by provider order
          3) Apply simple hint-based biasing (vision/deep_reasoning keywords)
        """
        # 1) Try explicit chains from auggie settings
        try:
            from auggie.config import get_auggie_settings

            settings = get_auggie_settings() or {}
            fb = settings.get("fallback") or {}
            key = None
            if category is not None:
                try:
                    # Map commonly used aliases
                    key = {
                        "FAST_RESPONSE": "chat",
                        "EXTENDED_REASONING": "reasoning",
                    }.get(category.name, category.name.lower())
                except Exception:
                    key = None
            chain = fb.get(key or "", [])
            if chain:
                # If hints provided, lightly bias order
                if hints:
                    low_map = {m.lower(): m for m in chain}
                    priorities: list[str] = []
                    for h in [s.lower() for s in hints if isinstance(s, str)]:
                        if any(k in h for k in ("vision", "image", "diagram")):
                            for cand in ("glm-4.5v",):
                                m = low_map.get(cand)
                                if m and m not in priorities:
                                    priorities.append(m)
                        if any(k in h for k in ("think", "reason", "chain of thought", "cot", "deep")):
                            for cand in ("kimi-k2-thinking", "kimi-k2-0711-preview", "glm-4.5-airx"):
                                m = low_map.get(cand)
                                if m and m not in priorities:
                                    priorities.append(m)
                    rest = [m for m in chain if m not in priorities]
                    return priorities + rest
                return chain
        except Exception:
            pass

        # 2) Derive a reasonable default ordering
        seed = cls.get_preferred_fallback_model(category)
        order: list[str] = [seed] if seed else []

        # Expand by provider priority, preserving per-provider allowed ordering
        instance = cls()
        for ptype in cls.PROVIDER_PRIORITY_ORDER:
            prov = cls.get_provider(ptype)
            if not prov:
                continue
            try:
                allowed = cls._get_allowed_models_for_provider(prov, ptype)
            except Exception:
                try:
                    allowed = prov.list_models(respect_restrictions=True)
                except Exception:
                    allowed = []
            for name in allowed:
                if name not in order:
                    order.append(name)

        # 3) Hint-based biasing
        if hints:
            low_map = {m.lower(): m for m in order}
            priorities = []
            for h in [s.lower() for s in hints if isinstance(s, str)]:
                if any(k in h for k in ("vision", "image", "diagram")):
                    for cand in ("glm-4.5v",):
                        m = low_map.get(cand)
                        if m and m not in priorities:
                            priorities.append(m)
                if any(k in h for k in ("think", "reason", "chain of thought", "cot", "deep")):
                    for cand in ("kimi-k2-thinking", "kimi-k2-0711-preview", "glm-4.5-airx"):
                        m = low_map.get(cand)
                        if m and m not in priorities:
                            priorities.append(m)
            rest = [m for m in order if m not in priorities]
            order = priorities + rest

        return order

    @classmethod
    def call_with_fallback(
        cls,
        category: Optional["ToolModelCategory"],
        call_fn,
        hints: Optional[list[str]] = None,
    ):
        """Execute call_fn(model_name) over a category-aware fallback chain.
        Records lightweight telemetry for each attempt and returns the first
        successful response. Raises the last exception if all attempts fail.
        """
        import time as _t

        chain = cls._auggie_fallback_chain(category, hints)
        last_exc: Exception | None = None
        for model in chain:
            t0 = _t.perf_counter()
            try:
                resp = call_fn(model)
                dt_ms = (_t.perf_counter() - t0) * 1000.0
                if resp is None:
                    # Record failure with no usage
                    cls.record_telemetry(model, False, latency_ms=dt_ms)
                    # JSONL error logging for None response
                    try:
                        from utils.observability import record_error
                        prov = cls.get_provider_for_model(model)
                        ptype = prov.get_provider_type() if prov else None
                        provider = getattr(ptype, "value", getattr(ptype, "name", "unknown")) if ptype else "unknown"
                        record_error(str(provider), model, "call_failed_none", "Provider returned None")
                    except Exception:
                        pass
                    raise RuntimeError(f"Provider returned None for model '{model}'")
                # Best-effort usage capture for success telemetry
                usage = getattr(resp, "usage", {}) or {}
                cls.record_telemetry(
                    model,
                    True,
                    input_tokens=int(usage.get("input_tokens", 0) or 0),
                    output_tokens=int(usage.get("output_tokens", 0) or 0),
                    latency_ms=dt_ms,
                )
                return resp
            except Exception as e:
                dt_ms = (_t.perf_counter() - t0) * 1000.0
                cls.record_telemetry(model, False, latency_ms=dt_ms)
                # JSONL error logging for exception
                try:
                    from utils.observability import record_error
                    prov = cls.get_provider_for_model(model)
                    ptype = prov.get_provider_type() if prov else None
                    provider = getattr(ptype, "value", getattr(ptype, "name", "unknown")) if ptype else "unknown"
                    record_error(str(provider), model, "call_failed", str(e))
                except Exception:
                    pass
                last_exc = e
                continue
        if last_exc:
            raise last_exc
        raise RuntimeError("No models available for fallback execution")

    @classmethod
    def get_telemetry(cls) -> dict[str, Any]:
        """Return a copy of telemetry data."""
        with cls._telemetry_lock:
            # Shallow copy is sufficient for reporting
            return {k: dict(v) for k, v in cls._telemetry.items()}

    @classmethod
    def clear_telemetry(cls) -> None:
        with cls._telemetry_lock:
            cls._telemetry.clear()
