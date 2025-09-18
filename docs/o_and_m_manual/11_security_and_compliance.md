# Security & Compliance

## Key practices
- Secrets only in `.env`; never commit them. Use `.env.example` for documented placeholders.
- Prefer package managers for dependency changes (avoid manual edits in requirements files).
- Safe-by-default runs: linters/tests are fine without permission; avoid destructive operations.

## MCP safety model
- Tools validate arguments; workflow tools require step metadata and findings.
- Activity logging (MCP_CALL_SUMMARY) provides per-call accountability.

## Secaudit workflow (OWASP-aligned)
1) Scope: select target code/config paths
2) Run `secaudit` with severity filter and focus (owasp/compliance/etc.)
3) Triage: fix critical/high issues first; document mitigations
4) Re-run secaudit; ensure 0 critical/high before release

## Release checklist
- [ ] `.env` present locally; no secrets in VCS
- [ ] Provider keys validated via `listmodels`
- [ ] Lint/tests pass (quality checks script)
- [ ] Secaudit: no critical/high findings
- [ ] Docs updated (O&M manual + sweep reports)

