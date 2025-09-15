"""Phase B Option B (disabled by default): providers.registry -> src.providers.registry shim.

This file is NOT imported anywhere by default. To opt-in later, replace
imports of `providers.registry` with `providers.registry_srcshim`, or set a flag
in a future refactor. It re-exports everything from src.providers.registry.
"""

from src.providers.registry import *  # noqa: F401,F403

