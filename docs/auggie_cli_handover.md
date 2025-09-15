# Auggie CLI Agent Handover

This document hands over the current state, changes, runbooks, and next steps for the Auggie CLI agent working against the EX AI MCP Server.

## TL;DR
- MCP server: exai-mcp is healthy and listening on `ws://127.0.0.1:8765`
- Final-step workflows now embed files using a safe, chunked reader (opt-in flag) to avoid token budget overruns
- Provider calls (GLM, Kimi) have minimal retry with exponential backoff and user‑friendly errors
- Workflow now attaches a machine‑readable JSON payload with embedded files for expert analysis
- Centralized secure path normalization for relevant_files is enabled in the workflow mixin when `SECURE_INPUTS_ENFORCED=true`
- Use `docs/agentic_upgrade_execution_log.md` to append each restart + validation outcome

## Key changes introduced in this iteration

1) Chunked file embedding for final/expert steps (opt-in)
- File: `utils/file_chunker.py`
- Flag: `CHUNKED_READER_ENABLED=true`
- Behavior: extracts salient sections (class/def/heading blocks) with a per‑file token budget; used only on final/expert steps
- Integrated in: `tools/workflow/workflow_mixin.py` — prefers chunked embedding when enabled and falls back gracefully

2) Provider resilience wrappers (GLM + Kimi)
- Files:
  - `src/providers/glm.py` — retry with backoff; friendly error messages
  - `src/providers/kimi.py` — mirrored behavior
- Flags: `RESILIENT_RETRIES` (default 2), `RESILIENT_BACKOFF_SECS` (default 1.5)

3) Expert analysis schema alignment
- File: `tools/workflow/workflow_mixin.py`
- Adds machine‑readable payload to expert context when files are embedded:
  - `files_in_payload`: `[{"path": "<basename>", "full_path": "<abs>"}, ...]`
  - `combined_embedded_content`: "<chunk>"
- Goal: avoid expert returning `files_required_to_continue` when the workflow already embedded content

4) Centralized SecureInputValidator for relevant_files
- File: `tools/workflow/workflow_mixin.py`
- When `SECURE_INPUTS_ENFORCED=true`, relevant_files are normalized centrally before embedding/reference, reducing per‑tool duplication

5) Scripts and testing helpers
- `scripts/ws_call_analyze.py` — Phase 1 only (no provider), quick local validation
- `scripts/ws_call_analyze_final.py` — Final step (provider enabled) to validate chunked embedding path

6) Documentation/logging
- Execution log: `docs/agentic_upgrade_execution_log.md` — append one block per run with: restart time+PID, call details, observation, outcome, next

## Environment & feature flags
- `CHUNKED_READER_ENABLED=true` — prefer chunked embedding on final/expert steps
- `RESILIENT_RETRIES=2`, `RESILIENT_BACKOFF_SECS=1.5` — provider retry/backoff tuning
- `SECURE_INPUTS_ENFORCED=true` — central path normalization for relevant_files in workflow mixin
- Optional (stability): `EXAI_WS_CALL_TIMEOUT=240` — if clients disconnect early while waiting for provider

## Starting / Restarting the MCP server
Windows PowerShell:
- `powershell -ExecutionPolicy Bypass -File .\scripts\ws_start.ps1 -Restart`
- Server listens on: `ws://127.0.0.1:8765`
- Logs:
  - `logs/mcp_server.log` (main)
  - `logs/mcp_activity.log` (tool calls)

## Quick validation runbook

1) Phase 1 (local, no provider)
- Command: `\.venv\Scripts\python.exe scripts\ws_call_analyze.py`
- Expect: `pause_for_analysis` with `reference_only` file_context; no provider call

2) Final step (chunked, provider on)
- Prereq: `.env` contains `CHUNKED_READER_ENABLED=true`
- Command: `\.venv\Scripts\python.exe scripts\ws_call_analyze_final.py`
- Expect:
  - Server logs show: `[WORKFLOW_FILES] analyze: Used CHUNKED reader for final step`
  - file_context: `fully_embedded`
  - Provider call success (HTTP 200)
  - No `files_required_to_continue` (expert should see `files_in_payload` + `combined_embedded_content` in context)

## File handling semantics (important)
- Intermediate steps (`next_step_required=true`): reference file names only (no embedding) to preserve context
- Final/expert steps (`next_step_required=false`): embed content
  - If `CHUNKED_READER_ENABLED=true`: chunked extraction (salient sections) within token budgets
  - Else: legacy full read within budgets (may skip if too large)
- Central secure normalization for `relevant_files` runs when `SECURE_INPUTS_ENFORCED=true`

## Provider behavior
- Model routing resolves a provider (GLM/Kimi) at the boundary; tool code uses that provider with resilience wrappers
- On transient network/429: retry with exponential backoff; on exhaustion: raise concise user‑friendly error while retaining full logs

## Execution log maintenance
- File: `docs/agentic_upgrade_execution_log.md`
- Append after every restart and validation
- Suggested block:
  - Timestamp+PID, env flags used
  - Call summary (tool, args)
  - Observations (log snippets worth noting)
  - Outcome (OK/needs follow‑up) + next steps

## Known issues / Open tasks
- Confirm expert no longer responds with `files_required_to_continue` after schema alignment; if still present:
  - Pass files as a first‑class structured argument to the expert payload instead of context text block
  - Consider reducing combined payload size further or attaching per‑file entries instead of a combined blob
- Unify per‑tool path normalization: remove any remaining duplicated SecureInputValidator logic inside individual tools now that workflow mixin centralizes it
- Stabilize client‑server timing: if ws client closes before response, increase `EXAI_WS_CALL_TIMEOUT` and/or emit more granular progress
- Enhance chunk selection heuristics: language‑aware section detection, bigger window for class methods, optional line numbers toggle
- Tests: add unit tests around chunker selection and provider retry; simulator tests for final‑step chunked flows

## Suggested tests to run
- Quick mode: `python communication_simulator_test.py --quick`
- Individual:
  - `python -m pytest tests/test_refactor.py::TestRefactorTool::test_format_response -v`
  - `python -m pytest tests/ -v -m "not integration"`
- Integration (optional, free local models): see `.augment-guidelines` for Ollama setup

## Operational runbook
- Quality checks: `./scripts/code_quality_checks.sh`
- Tail logs:
  - `tail -n 200 logs/mcp_server.log`
  - `tail -n 100 logs/mcp_activity.log`
- Common grep patterns:
  - `grep "[WORKFLOW_FILES]" logs/mcp_server.log`
  - `grep "TOOL_CALL\|TOOL_COMPLETED" logs/mcp_activity.log`

## Security & privacy
- Cost warning appears when expert analysis is invoked; disable by setting `use_assistant_model=false` (per request) or change default in `.env`
- Embedded content is sent to external providers only on final/expert steps; Phase 1 is local‑only

## Contact points in code
- Chunked reader: `utils/file_chunker.py`
- Resilient errors: `utils/resilient_errors.py`
- Workflow mixin (embedding, schema payload, normalization): `tools/workflow/workflow_mixin.py`
- Providers:
  - GLM: `src/providers/glm.py`
  - Kimi (Moonshot): `src/providers/kimi.py`
- Analyze WS drivers (validation helpers): `scripts/ws_call_analyze.py`, `scripts/ws_call_analyze_final.py`

## Handoff checklist for next Auggie CLI agent
- [ ] Restart server, confirm exai-mcp ready
- [ ] Run Phase 1 analyze and log outcome
- [ ] Run final-step analyze (chunked) and confirm no `files_required_to_continue`
- [ ] If expert still requests files: switch to structured file payload attached to the expert call itself
- [ ] Remove duplicated path‑normalization in individual tools (if any remain)
- [ ] Run quick simulator tests; fix any regressions
- [ ] Update `docs/agentic_upgrade_execution_log.md` for every action


## Quick Start: Auggie CLI with EXAI MCP (exai-mcp)

This section gives a copy/paste path to re-run Auggie CLI using the EX AI MCP Server (exai-mcp) as the MCP backend.

### Prereqs
- Python venv created with dependencies and a valid .env configured (provider keys or CUSTOM_API_URL if you want provider calls)
- Logs directory exists: `logs/`

### 1) Start/Restart the WS daemon (server)
Windows PowerShell (already validated in prior sections):
- `powershell -ExecutionPolicy Bypass -File .\scripts\ws_start.ps1 -Restart`
- Expect: server listening on `ws://127.0.0.1:8765` and tools listed in logs

Alternative (new terminal window/tab)
- Using Windows Terminal tab:
  - `wt -w 0 nt powershell -NoExit -d . -c "Set-Location 'c:\Project\EX-AI-MCP-Server'; .\.venv\Scripts\Activate.ps1; python -u scripts\run_ws_daemon.py | Tee-Object -FilePath logs\ws_daemon.out -Append"`

### 2) Choose the MCP config file for Auggie CLI
The repo includes 3 example client configs under `Daemon/`:
- `mcp-config.auggie.json` (uses top-level `servers`) – recommended for Auggie CLI
- `mcp-config.augmentcode.json` (uses top-level `mcpServers`) – Augment Code style
- `mcp-config.claude.json` (uses top-level `servers`) – Claude-style

All three point to the same shim runner: `scripts/run_ws_shim.py` which connects to the WS daemon on `127.0.0.1:8765`.

### 3) Launch Auggie CLI with EXAI MCP
- Basic launch:
  - `auggie --mcp-config "C:\Project\EX-AI-MCP-Server\Daemon\mcp-config.auggie.json"`
- You should see: `MCP Server Status: ✅ exai-mcp (ready)`

### 4) Quick validation calls via Auggie
- List tools:
  - `auggie tools list --mcp-config "C:\Project\EX-AI-MCP-Server\Daemon\mcp-config.auggie.json"`

- Phase 1 analyze (local-only, fast):
  - `auggie tool call analyze --mcp-config "C:\Project\EX-AI-MCP-Server\Daemon\mcp-config.auggie.json" --args '{"step":"Kickoff","step_number":1,"total_steps":1,"next_step_required":true,"use_assistant_model":false,"findings":"auggie phase1","analysis_type":"general","output_format":"summary","relevant_files":["server.py"]}'`
  - Expect: `file_context.type = reference_only`, `continuation_id` present, no provider call

- Final-step analyze (chunked + provider):
  - Ensure `.env` or shell has `CHUNKED_READER_ENABLED=true`
  - `auggie tool call analyze --mcp-config "C:\Project\EX-AI-MCP-Server\Daemon\mcp-config.auggie.json" --args '{"step":"Final step","step_number":1,"total_steps":1,"next_step_required":false,"use_assistant_model":true,"findings":"auggie final","analysis_type":"general","output_format":"summary","relevant_files":["server.py"]}'`
  - Expect: `file_context.type = fully_embedded` and logs show `[WORKFLOW_FILES] analyze: Used CHUNKED reader for final step`; expert analysis should not ask for `files_required_to_continue`

### 5) Health check and logs
- Daemon status: `python scripts\ws_status.py`
- Main logs:
  - `Get-Content -Path logs\mcp_server.log -Wait -Tail 200`
  - Quick grep: `Select-String -Path logs\mcp_server.log -Pattern "[WORKFLOW_FILES]|[CONTEXT_OPTIMIZATION]"`

### Common pitfalls
- Using a config file with the wrong top-level key for your client (`servers` vs `mcpServers`). Use the `auggie` variant for Auggie CLI.
- Final-step calls without `CHUNKED_READER_ENABLED=true` may be slow or exceed token budgets on large files.
- Provider calls require configured keys (KIMI_API_KEY / GLM_API_KEY / OPENROUTER_API_KEY) or a local `CUSTOM_API_URL`.

### After each run
- Append results to `docs/agentic_upgrade_execution_log.md` with timestamp, PID, env flags, call summary, outcome, and next steps.
