# Migration Checklist — Phase A (Providers)

Scope: Non-destructive shims + documentation only

- [x] Freeze top-level providers/* with deprecation headers
- [x] Add sys.modules shims in providers/__init__.py to point to src/providers/*
- [x] Add providers/README explaining the shim window and removal plan
- [x] Restore Augment docs folder and index
- [ ] Grep for legacy imports `from providers.` in repo and update to `from src.providers.` where feasible
- [ ] Run smoke validations: listmodels tool, quick GLM/Kimi chat
- [ ] Confirm only src/providers registry is used at runtime (log check)
- [ ] Plan deletion window after green CI period

Validation notes
- If both registries are imported anywhere, decision paths can diverge; ensure imports converge on src/providers
- Keep this checklist updated as we proceed to Phases B/C

