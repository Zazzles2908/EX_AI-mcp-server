# Phase‑1 Cleanup Report — Archive Moves and Validation

Date: (auto)
Author: Augment Agent (via EXAI‑MCP)

## Scope
We archived non‑essential files and directories into `archive/phaseD_cleanup/` while preserving all runtime‑critical components (stdio MCP server, WS daemon + shim, tools registry, providers, routing).

## Items moved
- README-ORIGINAL.md → archive/phaseD_cleanup/docs_legacy/README-ORIGINAL.md
- scripts/progress_test.py → archive/phaseD_cleanup/scripts_dev/progress_test.py
- scripts/run_inline_exai_phase1_review.py → archive/phaseD_cleanup/scripts_dev/run_inline_exai_phase1_review.py
- nl/ → archive/phaseD_cleanup/features_future/nl/
- ui/ → archive/phaseD_cleanup/features_future/ui/
- dr/ → archive/phaseD_cleanup/features_future/dr/
- patch/ → archive/phaseD_cleanup/patch_legacy/
- docs/standard_tools → archive/phaseD_cleanup/docs_pruned/standard_tools
- docs/cleanup → archive/phaseD_cleanup/docs_history/cleanup
- docs/mcp_tool_sweep_report.md → archive/phaseD_cleanup/docs_history/mcp_tool_sweep_report.md

## Rationale
- None of these are imported by `server.py`, `src/daemon/*`, `tools/*`, or `providers/*` at runtime.
- They represent legacy docs, dev helpers, or future/unused stubs.

## Validation (EXAI‑MCP)
- Ran `precommit_EXAI‑WS` to analyze the change impact across the repository.
- Result: Completed without reported breakage indicators or references to archived paths from runtime modules.

## Notes
- Streaming adapters, tool registry, providers, stdio server entrypoint, and WS daemon remain untouched.
- Docker, remote_server, and monitoring were intentionally kept for now.

## Next considerations (Phase‑2+)
- Evaluate `monitoring/` and example Docker assets for archival vs. modernization.
- Cross‑check docs for links pointing to archived paths and update as needed.

## Phase-3 link-check and Start Here
- Ran a repo-wide markdown link-check focused on docs/. No runtime references are affected by docs moves.
- One false positive flagged inside a code block in docs/external_review/exai_agentic_upgrade_report.md ("e, attempt")  not a markdown link. No actual broken links found.
- Updated navigation by adding docs/index.md (curated start page) pointing to O&M manual, architecture, external_review, sweep_reports, personal quickstart, and policies.

## Rollback
All moves used `git mv`, enabling simple revert using git history if needed.

