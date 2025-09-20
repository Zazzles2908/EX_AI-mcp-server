# Non-test Legacy Import Blocker (providers.* / routing.*)

Status: Enabled via CI (GitHub Actions)

What it does
- Fails builds if any non-test source file imports legacy modules:
  - `from providers...` / `import providers...`
  - `from routing...` / `import routing...`
- Exclusions: `tests/**`, `providers/**` (shim), `routing/**` (shim), `.venv`, `venv`, `.git`, `dist`, `build`, `__pycache__`, `docs/**`

How it runs
- Script: `scripts/check_no_legacy_imports.py`
- CI: `.github/workflows/no-legacy-imports.yml` runs the script on push/PR to `main` and `feat/**`

Local usage
```bash
python scripts/check_no_legacy_imports.py
```

Rationale
- Prevent mixed-tree regressions while shims exist
- Keep canonical imports on `src.providers.*` and `src.router.*`

Next steps
- Keep blocker until shims (providers/*, routing/*) are deleted post green window.

