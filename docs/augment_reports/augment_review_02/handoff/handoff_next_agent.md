# EXAI-WS MCP Stabilization — Handoff Runbook (Next Agent)

This document is a self-contained, actionable checklist for continuing the EXAI-WS MCP stabilization, completing validation (target PASS 11/11), generating final reports, and wrapping up documentation/PR.

## 1) Context & Environment Snapshot
- Workspace root: c:\Project\EX-AI-MCP-Server
- WebSocket endpoint: ws://127.0.0.1:8765 (also try ws://127.0.0.1:8765/ws)
- Validation script: scripts/validate_exai_ws_kimi_tools.py (no --fast)
- Validation artifacts dir: docs/augment_reports/augment_review_02/validation/runs/<timestamp>
- Final validation report target: docs/augment_reports/augment_review_02/validation/validation_report_2025-09-21.md
- Kimi analysis docs (to finalize): docs/augment_reports/augment_review_02/kimi_analysis/*.md
- Key env (.env) — ensure present and correct:
  - KIMI_API_KEY=...  (required)
  - KIMI_DEFAULT_MODEL=kimi-k2-0711-preview
  - GLM model keys as configured (glm-4.5-flash etc.)
  - FILECACHE_ENABLED=true
  - KIMI_FILES_FETCH_RETRIES=3, KIMI_FILES_FETCH_BACKOFF=0.8, KIMI_FILES_FETCH_INITIAL_DELAY=0.5
  - EXAI_WS_OPEN_TIMEOUT=60
  - EXAI_WS_PING_INTERVAL=45
  - EXAI_WS_PING_TIMEOUT=120
  - EXAI_WS_CLOSE_TIMEOUT=10
  - (Server tool timeout, if available) EXAI_WS_TOOL_TIMEOUT or TOOL_EXEC_TIMEOUT_SEC >= 60

## 2) Current Status & Known Issues
- Deprecation warning resolved in validator (asyncio.run in place).
- Previously observed: PASS 10/11; remaining issue: kimi_multi_file_chat cancelled ~5s after uploads (TOOL_CANCELLED) and subsequent WS closure.
- Validator enhancements added:
  - websockets.connect open_timeout/ping/close tuned via env; URI fallbacks (/, /ws; optional MCP_REMOTE_PORT)
- Provider tools updated:
  - GLMUploadFileTool and KimiMultiFileChatTool now implement async execute() using to_thread; upload_and_extract uses _run() and retries for content fetch.

## 3) Quick Sanity Checks (Before Final Run)
- Confirm EXAI-WS daemon running and listening on ws://127.0.0.1:8765
- Confirm list_tools shows: chat, analyze, thinkdeep, planner, kimi_upload_and_extract, kimi_multi_file_chat, glm_upload_file, glm web search, CLI cleanup
- If server logs show short tool timeout (< 60s), increase EXAI_WS_TOOL_TIMEOUT or TOOL_EXEC_TIMEOUT_SEC and restart the daemon.

## 4) Final Validation Execution
- Command: python -X utf8 scripts/validate_exai_ws_kimi_tools.py
- Expected:
  - PASS 11/11 with real, non-hardcoded outputs
  - Artifacts saved under docs/augment_reports/augment_review_02/validation/runs/<timestamp>
- If handshake/keepalive issues reappear:
  - Try ws://127.0.0.1:8765/ws path
  - Raise EXAI_WS_OPEN_TIMEOUT to 90
  - Verify firewall/AV exclusions

## 5) If Failures Persist (Minimal Fixes)
- Avoid introducing new compatibility flags.
- Only adjust server tool timeout env (>= 60–90s) or reduce concurrency/batch sizes.
- Re-run validation; log errors under docs/audit/errors_logged/call_errors.md

## 6) Generate Final Validation Report
- Path: docs/augment_reports/augment_review_02/validation/validation_report_2025-09-21.md
- Include:
  - Pass matrix (tool-by-tool), total duration
  - Env snapshot and WS endpoint used
  - Links to run artifacts
  - Real EXAI-WS outputs for unpredictable prompts (per user preference)
  - Brief root-cause summary of any fixes applied (timeouts, etc.)

## 7) Complete Kimi Analysis Docs
- Replace all PENDING/IN PROGRESS placeholders in docs/augment_reports/augment_review_02/kimi_analysis/*.md
- Use EXAI-WS analyze (Kimi) and ThinkDeep for synthesis; preserve raw outputs for traceability.

## 8) Task Manager Reconciliation
- Mark Phase 1–4 tasks COMPLETE after PASS 11/11
- Deduplicate any duplicate “Current Task List” entries
- Keep exactly one task In Progress at a time; batch state updates

## 9) Branch & PR (gh-mcp)
- Create/switch to branch: mcp-tool-stabilization-final (never push to main directly)
- Push branch, open PR
- Ensure no credentials/large files; include validation artifacts and markdown report links

## 10) Acceptance Criteria
- PASS 11/11 with clean logs (no deprecation warnings)
- Provider tools execute via async execute() and return TextContent JSON payloads
- Artifacts under validation/runs and final report present with links
- Kimi analysis docs completed with authoritative EXAI-WS outputs
- Task manager updated; PR created and ready for merge review

## 11) Risks & Fallbacks
- WS instability: use /ws path, increase open_timeout, verify local firewall
- Tool cancellation: increase server tool timeout to 60–90s; serialize uploads if needed
- Provider throttling: respect KIMI_FILES_FETCH_* backoff and retry; reduce parallelism

## References
- docs/external_review/auggie_cli_agentic_upgrade_prompt.md
- scripts/validate_exai_ws_kimi_tools.py (WS keepalive/open timeout settings)
- tools/providers/kimi/kimi_upload.py (execute/_run for Kimi tools)
- tools/registry.py (TOOL_MAP and visibility)

-- End of Handoff --

