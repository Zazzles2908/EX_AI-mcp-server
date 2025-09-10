"""src.providers package

Exports the model provider registry, base types, and concrete providers.
This is now the source of truth; legacy `providers.*` serves as a shim.
"""

from .base import (
    ModelProvider,
    ModelCapabilities,
    ModelResponse,
    ProviderType,
    TemperatureConstraint,
    FixedTemperatureConstraint,
    RangeTemperatureConstraint,
    DiscreteTemperatureConstraint,
    create_temperature_constraint,
)
from .registry import ModelProviderRegistry

# Do NOT import concrete providers at package import time to avoid side effects
# (e.g., optional deps, environment not ready). Import them explicitly where needed.

__all__ = [
    "ModelProvider",
    "ModelCapabilities",
    "ModelResponse",
    "ProviderType",
    "TemperatureConstraint",
    "FixedTemperatureConstraint",
    "RangeTemperatureConstraint",
    "DiscreteTemperatureConstraint",
    "create_temperature_constraint",
    "ModelProviderRegistry",
]
