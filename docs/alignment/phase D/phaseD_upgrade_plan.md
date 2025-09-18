# Phase D Upgrade Plan — Minimal‑Risk Stabilization

D1 — Toolchain Sanity + Evidence
- Actions:
  - Verify EXAI‑MCP status/chat/analyze via direct calls
  - Capture evidence to docs/alignment/mcp_runs and phase4 sweep
- Acceptance:
  - status TOOL_CALL present, chat/analyze TOOL_COMPLETED in mcp_activity.log
  - Evidence MD added with timestamps and models

D2 — Router Observability + Summary Integrity
- Actions:
  - Confirm [ROUTER_DECISION] from utils/model_router.py appears during tool calls
  - Confirm MCP Call Summary header is prepended (server + BaseTool)
- Acceptance:
  - Logs show tool, requested, choice; summary header visible in returned content or server logs

D3 — Documentation Restore + Safety
- Actions:
  - Restore/re‑synthesize Phase D docs (README, upgrade_plan, checklist)
  - Keep work isolated on feat/docs-restore-phaseD-from-stash; no push yet
- Acceptance:
  - Files exist and are committed on safety branch only

D4 — Evidence Cadence
- Actions:
  - Create small, repeatable smoke scripts (prompt snippets) for chat/analyze/testgen/codereview
  - Save outputs summary lines (timestamps, models) in docs/alignment/mcp_runs
- Acceptance:
  - At least one fresh run captured after daemon/VS Code restart

D5 — Hardening (Optional, post‑sign‑off)
- Actions:
  - Add server‑side fallback status snapshot if status tool fails to register
  - Add lightweight health probe to write ws_daemon.health.json periodically
- Acceptance:
  - Graceful degradation path documented; toggled off by default

Branching and Risk Controls
- Work only on feat/docs-restore-phaseD-from-stash until owner confirms
- No pushes until owner reviews evidence
- Strictly no secrets; .env guidance stays minimal; use .env.example for detail

Definition of Done (Phase D)
- EXAI‑MCP tools functional: status/chat/analyze/codereview/testgen
- Router decisions and MCP Call Summary verified
- Evidence files present and linked from Phase D README
- Phase D docs (README/Plan/Checklist) merged by owner after review
