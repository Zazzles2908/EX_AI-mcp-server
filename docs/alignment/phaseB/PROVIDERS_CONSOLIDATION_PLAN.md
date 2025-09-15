# Phase B: Providers Consolidation Plan (Draft)

Objective: Eliminate the dual provider layers (`providers/` at project root and `src/providers/`) by consolidating to `src/providers/` with import-compat shims. Keep changes low-risk and reversible.

## Why
- Mixed imports increase ambiguity and runtime variance
- Onboarding complexity and test brittleness
- Enables clearer model routing and configuration

## Target State
- Single canonical path: `src/providers/`
- Thin re-export shims in `providers/` that forward imports to `src/providers/`
- All internal imports updated to canonical path over time

## Steps
1) Inventory
   - Map modules in `providers/` vs `src/providers/` (glm, kimi, router, base)
   - Identify duplicates and the version to keep
2) Create shims
   - For each module in `providers/`, create a 3–5 line shim that re-exports the class/functions from `src/providers/...`
   - Example shim:
     ```python
     # providers/kimi.py (shim)
     from src.providers.kimi import KimiModelProvider
     __all__ = ["KimiModelProvider"]
     ```
3) Update canonical imports
   - In code we own (non-public API), switch to `from src.providers...`
   - Leave external/public-facing imports working via shims
4) Tests
   - Run unit tests
   - Run quick integration tests (local model if configured)
5) Removal window
   - After N releases, delete shims and update remaining imports

## Risks & Mitigation
- Risk: Hidden external code imports `providers.*`
  - Mitigation: Keep shims until deprecation window ends
- Risk: Divergent versions
  - Mitigation: Freeze edits to `providers/` and accept changes only in `src/providers/`

## Validation Checklist
- [ ] All imports resolve when shims are active
- [ ] Unit tests pass
- [ ] Router selects GLM flash by default; Kimi used only when explicitly routed
- [ ] No mixed path warnings in logs

