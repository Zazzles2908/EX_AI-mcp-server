## EXAI-WS MCP Validation Report — 2025-09-21

Top-line (YES/NO)
YES — Core workflows (chat, thinkdeep, analyze step 1→2) validated OK. Provider-surface MCP tools (kimi/glm file APIs) are not exposed and CLI cleanup failed due to import path. Script-based validation is integrated and repeatable.

Run artifacts
- Fast run: docs/augment_reports/augment_review_02/validation/runs/run_20250921T122515Z/
- Prior run (pre-fix): docs/augment_reports/augment_review_02/validation/runs/run_20250921T122346Z/

Pass/Fail snapshot
- PASS: chat (Kimi), chat (GLM flash), thinkdeep, analyze (step 1, step 2)
- FAIL (not exposed): kimi_upload_and_extract, kimi_multi_file_chat, glm_upload_file
- CLI extras: embeddings (skipped — KIMI_EMBED_MODEL unset), cleanup (rc=1, import path error)

Key findings
- Continuation: analyze step 1 must NOT include continuation_id; step 2 works independently without explicit cont. Our script now reflects this and passes.
- Provider-surface MCP tools are not present in list_tools → likely gated by visibility (advanced/hidden) or registry omissions. This blocks MCP validation for Kimi file upload/multi-file chat via WS.
- CLI cleanup failed with ModuleNotFoundError: src not on PYTHONPATH when executed by path. The script captured stderr; likely fix is adjusting sys.path/PROJECT_ROOT calculation in tools/providers/kimi/kimi_files_cleanup.py or invoking with PYTHONPATH=.

Actionable next steps
1) Expose provider tools via registry/visibility
   - Ensure tools/providers/kimi {kimi_upload_and_extract, kimi_multi_file_chat} and GLM upload tool are registered in tools/registry.py and visible under current LEAN_MODE/TOOL_VISIBILITY.
   - Confirm with list_tools that names appear; re-run validation.
2) (Optional) Add an MCP wrapper for embeddings and cleanup
   - If desired coverage: implement kimi_embeddings and kimi_files_cleanup as MCP tools (advanced visibility) to test via WS instead of CLI.
3) Fix Kimi cleanup CLI import path
   - Update PROJECT_ROOT/sys.path math or run with PYTHONPATH=. Our validation script can set env for the subprocess; alternatively, patch the CLI.
4) Re-run full validation (no --fast) and append results.

Evidence excerpts
- analyze(step1) preview includes continuation_id and pause_for_analysis state; step2 calls expert analysis and completes.
- Provider-surface: "not_exposed" recorded for kimi/glm file tools.
- CLI cleanup stderr captured: ModuleNotFoundError: No module named 'src'.

Next validation cycle
- After exposing provider tools, run: python -X utf8 scripts/validate_exai_ws_kimi_tools.py
- Confirm all MCP tools: chat, analyze, thinkdeep, planner, kimi_* (upload/multi), glm_* (upload), tracer, etc. Document deltas.

