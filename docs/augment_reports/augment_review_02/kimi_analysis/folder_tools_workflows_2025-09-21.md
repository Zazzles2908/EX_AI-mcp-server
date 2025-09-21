# Phase 2 – Folder Analysis: tools/workflows

Status: IN PROGRESS (autonomous fill; will be overwritten by Kimi Step 2 output on arrival)
Date: 2025-09-21

Observed files
- analyze.py, thinkdeep.py, planner.py, codereview.py, debug.py, refactor.py, precommit.py, secaudit.py, testgen.py, tracer.py

Status & gaps
- analyze, thinkdeep, planner: working; continuation_id and step gating confirmed
- others: likely schema/descriptor parity needed; align timeouts and output formatting

Best practices
- Standardize request models (step, step_number, total_steps, next_step_required, findings, relevant_files, output_format)
- Enforce TOOL_EXEC_TIMEOUT_SEC and workflow-specific timeouts; add progress heartbeats where missing
- Ensure consistent ui_summary (when enabled) and safe text aggregation (EXAI_WS_COMPAT_TEXT)

Concrete fixes
1) Verify each tool exposes get_descriptor() with accurate schema
2) Normalize error messages and validation for relevant_files
3) Add retries/backoff on provider calls inside workflows that invoke providers
4) Ensure minimal outputs are non-empty (server-side guard in place; add tool-level fallbacks where appropriate)

Validation
- Run minimal calls for each workflow tool post-fix; capture outputs and update docs with examples
