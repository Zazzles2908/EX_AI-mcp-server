"""Provider package exports and legacy shims.

- Exports base types and the registry
- Provides compatibility shims so `from providers.<mod> ...` keeps working
  after the migration to `src.providers`.
"""

from .base import ModelCapabilities, ModelProvider, ModelResponse  # noqa: F401
from .registry import ModelProviderRegistry  # noqa: F401

__all__ = [
    "ModelProvider",
    "ModelResponse",
    "ModelCapabilities",
    "ModelProviderRegistry",
]

# Backward-compatibility: alias selected submodules to src.providers.*
# This allows imports like `from providers.custom import CustomProvider` to continue working
import sys as _sys

try:
    from src.providers import custom as _src_custom
    _sys.modules.setdefault("providers.custom", _src_custom)
except Exception:
    pass

try:
    from src.providers import openrouter as _src_openrouter
    _sys.modules.setdefault("providers.openrouter", _src_openrouter)
except Exception:
    pass

try:
    from src.providers import openrouter_registry as _src_openrouter_registry
    _sys.modules.setdefault("providers.openrouter_registry", _src_openrouter_registry)
except Exception:
    pass

try:
    from src.providers import registry as _src_registry
    _sys.modules.setdefault("providers.registry", _src_registry)
except Exception:
    pass


try:
    from src.providers import capabilities as _src_capabilities
    _sys.modules.setdefault("providers.capabilities", _src_capabilities)
except Exception:
    pass

try:
    from src.providers import metadata as _src_metadata
    _sys.modules.setdefault("providers.metadata", _src_metadata)
except Exception:
    pass


# Additional legacy re-exports to src.providers.* (non-destructive shims)
try:
    from src.providers import base as _src_base
    _sys.modules.setdefault("providers.base", _src_base)
except Exception:
    pass

try:
    from src.providers import openai_compatible as _src_oac
    _sys.modules.setdefault("providers.openai_compatible", _src_oac)
except Exception:
    pass

try:
    from src.providers import glm as _src_glm
    _sys.modules.setdefault("providers.glm", _src_glm)
except Exception:
    pass

try:
    from src.providers import kimi as _src_kimi
    _sys.modules.setdefault("providers.kimi", _src_kimi)
except Exception:
    pass

try:
    from src.providers import zhipu_optional as _src_zhipu_opt
    _sys.modules.setdefault("providers.zhipu_optional", _src_zhipu_opt)
except Exception:
    pass

# Package-level shims (packages map cleanly to src packages)
try:
    from src.providers import moonshot as _src_moonshot
    _sys.modules.setdefault("providers.moonshot", _src_moonshot)
except Exception:
    pass

try:
    from src.providers import zhipu as _src_zhipu
    _sys.modules.setdefault("providers.zhipu", _src_zhipu)
except Exception:
    pass

# Deprecation note: top-level providers.* modules are shims. Canonical lives in src/providers.
# Pre-populated sys.modules above maps submodules to src.providers so imports resolve consistently.
