# Phase D Verification & Acceptance Checklist

Connectivity and Tools
- [ ] status tool callable (registry lists tools, providers GLM+Kimi)
- [ ] chat tool completes (glm-4.5-flash or kimi-k2 family visible in logs)
- [ ] analyze tool completes step 1 (TOOL_COMPLETED in activity log)
- [ ] codereview and testgen callable (at least one recent run)

Routing and Summary
- [ ] [ROUTER_DECISION] logs emit tool/profile/requested/choice
- [ ] MCP Call Summary header present at top of responses
- [ ] Duration band labels (fast/moderate/slow) look reasonable
- [ ] Cost labels (low/medium/high) match chosen model tier

Documentation
- [ ] docs/alignment/phase D/README.md present
- [ ] docs/alignment/phase D/phaseD_upgrade_plan.md present
- [ ] docs/alignment/phase D/phaseD_checklist.md present
- [ ] docs/alignment/phase D/PR1_log.md present (restored)

Evidence
- [ ] docs/alignment/mcp_runs/* contains latest stability and direct-call snapshots
- [ ] docs/sweep_reports/phase4_exai_review/* contains validation summary

Branch Hygiene
- [ ] All changes on feat/docs-restore-phaseD-from-stash
- [ ] No pushes to remote until owner confirms
- [ ] No credentials or large files added

Sign-off
- [ ] Owner reviewed evidence and approves merge into main
