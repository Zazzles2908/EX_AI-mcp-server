# providers (legacy shim)

This package provides backward-compatible shims during the consolidation to `src/providers`.

- Canonical home: `src/providers`
- Top-level `providers/*` modules are deprecated and frozen.
- `providers/__init__.py` pre-populates `sys.modules` so imports like `from providers.glm import GLMModelProvider` resolve to `src.providers.glm`.

Removal plan:
- Phase A (current): shims only, no behavior changes
- Phase E/F: delete legacy files after a green window and grep-clean of `from providers.*` imports

If you are implementing new provider functionality, put it under `src/providers` only.

