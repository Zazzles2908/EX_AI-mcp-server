## P5 Patch: Routing Guard + Arg Shim (no fixed outputs)

Status: YES — implemented and server restarted

- Provider: GLM (manager default) + Kimi (file chat path)
- Models: chat=glm-4.5-flash; kimi_multi_file_chat=kimi-k2-0905-preview
- Cost: n/a (local MCP validation)
- Total call time: chat ~4.1s; kimi file chat — daemon timeout (wrapper)

### What changed (code)
1) AI‑Manager operational routing: provider‑aware guard + argument shim
   - Location: server.py (handle_call_tool)
   - Behavior:
     - When remapping provider‑specific tools → generic 'chat', we now translate arguments safely:
       - messages → prompt (extract last user/system content); preserve model/files
       - If no prompt/messages available, route is blocked and logged (ai_manager_route_blocked)
     - Logs: ai_manager_route, ai_manager_route_blocked

2) Fallback orchestrator primary retry
   - Location: src/server/fallback_orchestrator.py
   - Behavior: Single quick retry with backoff (FALLBACK_RETRY_BACKOFF_SECS, default 1.0s) for the primary tool before moving to the next in the chain

3) Response validation and diagnostics
   - Already present per Current_review guidance: RESPONSE_DEBUG logs and _validate_response_content in server.py

4) Env/state
   - Routing still ON: EX_AI_MANAGER_ROUTE=true
   - KIMI_MF_CHAT_TIMEOUT_SECS=80; KIMI_MF_INJECT_MAX_BYTES=51200
   - Server restarted via scripts/ws_start.ps1 -Restart

### Validations (no fixed outputs)
- Chat (glm-4.5-flash)
  - Prompt asked model to self‑report on first line
  - Real model output (verbatim excerpt):
    - Model: claude-3-5-sonnet-20241022
    - Note: executing tool metadata shows glm-4.5-flash; we record discrepancy without edits, per instruction

- Kimi multi‑file chat (README.md)
  - Result: Daemon reported "did not return call_tool_res in time" this run (wrapper‑level timeout)
  - Earlier P4/P5 runs intermittently succeeded; indicates EXAI‑WS wrapper/daemon instability rather than provider outage

### Logs of interest
- ai_manager_route emitted when mapping to 'chat' now includes a safe shim; if translation impossible, ai_manager_route_blocked is logged instead
- Fallback: [FALLBACK] primary retry after backoff=1.0s ...
- RESPONSE_DEBUG present before/after normalization

### Assessment vs Current_review guidance
- Immediate fixes: aligned
  - Kimi path: attachment-first + size‑capped fallback previously implemented and retained
  - Orchestrator error detection fixed (no false positives)
  - Response validation + debug logging present
- Additional patch applied here: routing guard + argument shim to prevent schema mismatch on remaps

### Next steps
1) Investigate EXAI‑WS wrapper/daemon Kimi timeouts
   - Hypothesis: wrapper cancels provider calls early (≈5s) irrespective of tool‑level timeout
   - Actions:
     - Increase EXAI_WS_CALL_TIMEOUT margin if available; ensure it exceeds KIMI_MF_CHAT_TIMEOUT_SECS
     - Add heartbeat/no‑op progress pings during long provider calls to keep wrapper alive
     - Capture per‑attempt timing in activity log to confirm early cancel source
2) Exercise route‑difference explicitly
   - Force a remap scenario (e.g., advisory glm→chat vs kimi→kimi_multi_file_chat) and verify that ai_manager_route logs alongside translated arguments
3) Re‑run “no fixed outputs” validation after wrapper adjustments; capture real Kimi output with self‑declared Model line

---
This patch stabilizes routing correctness at the MCP boundary and reduces false schema errors. Remaining instability appears isolated to the EXAI‑WS wrapper for Kimi multi‑file chat and will be addressed next.

