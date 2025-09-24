# P1 Stress Validation — Dispatcher DRY-RUN + Kimi Multi-File Chat

Status: YES
- Provider: KIMI (Moonshot)
- Model: kimi-k2-0905-preview
- Call time: ~4.1s
- Outcome: SUCCESS (real output with file_id)

## Server
- Action: Restarted via scripts/ws_start.ps1 -Restart
- Result: OK (server running)

## Validation 1 — Kimi multi_file_chat (explicit Kimi)
- Files: [README.md]
- Prompt (unpredictable nonce):
  "Open the provided README.md and extract the first top-level heading text. Reply with: 1) The exact heading on its own line, 2) A single concise sentence summarizing the README in your own words, 3) Append this nonce token at the end of the sentence exactly as shown (keep the spaces): purple-sunbeam 9f72c1. Do not include any extra commentary."
- File IDs: ["d397u721ol7h6f24goc0"] (returned by Kimi)
- Output (verbatim):

```
# README

This repository documents a Python-based project that provides utilities for data processing and visualization. purple-sunbeam 9f72c1
```

Notes:
- Output includes the requested nonce and heading, indicating real model execution against the uploaded file.

## Dispatcher DRY-RUN
- Change: Added a dry-run log inside handle_call_tool (env-gated by EX_USE_DISPATCHER); no behavior change
- Log format: [DISPATCHER-DRYRUN] req_id=<uuid> tool=<name> model_hint=<auto|model>
- Purpose: Confirm future routing signals without altering execution

## Next
- Continue stress tests to exercise circuit breakers (forced failures/timeouts) and document open/half-open/cool-off behavior.
- Begin safe modularization wiring (telemetry/registry_bridge touchpoints; restart after each edit).
