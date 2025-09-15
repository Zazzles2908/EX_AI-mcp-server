# Phase B Option B (Staged, Disabled): providers.registry -> src.providers.registry

Status: STAGED, not active. This is a safety valve to flip to the canonical `src.providers.registry`
implementation once pilots complete.

## What is staged
- `providers/registry_srcshim.py` — re-exports from `src.providers.registry`.
- Not referenced anywhere; zero runtime effect today.

## How to activate later (one of):
1) Minimal import swap in code you control:
   - Replace `from providers.registry import ModelProviderRegistry` with
     `from providers.registry_srcshim import ModelProviderRegistry`.
2) Or consolidate: move/replace `providers/registry.py` with a re-export of `src.providers.registry`
   after pilots stabilize and tests pass.

## Rollout plan
- Keep this staged until:
  - At least 2 provider and 2 tool shims are live without regressions
  - Quick test suite is green
- Then activate in a small PR and run the full quality checks.

## Rationale
- Prevents drift between duplicate registries
- Gives a one-switch path to canonicalize without big-bang risk

