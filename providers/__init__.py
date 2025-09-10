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
