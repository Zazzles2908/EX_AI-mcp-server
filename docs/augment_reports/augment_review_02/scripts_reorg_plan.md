# Scripts Reorg Plan (Phase P2)

Goal: Organize scripts/ into canonical subfolders with backward-compatible wrappers.

Target structure:
- scripts/validation/
- scripts/diagnostics/
- scripts/ws/
- scripts/e2e/
- scripts/tools/
- scripts/kimi_analysis/
- scripts/legacy/

Plan:
1) Create subfolders and add README stubs.
2) For each existing script, add a wrapper in its new home and keep a shim at the old path that imports/executes the new entry point.
3) Update docs and CI to call the new locations.

Compatibility:
- All old script paths continue to work via thin shims for at least one release.

Next actions:
- Generate folder READMEs and enumerate current scripts.
- Draft shims for the top 3 frequently used scripts.

