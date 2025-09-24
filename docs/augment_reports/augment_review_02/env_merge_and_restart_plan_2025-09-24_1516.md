# Env merge + restart plan — Batch A

One-liner: YES — .env remains authoritative; merged commented, default-off gating and OpenAI-compatible base_url entries; server restarts will be automated via PowerShell.

## Changes
- .env: added commented entries (default-off):
  - TOOLS_CORE_ONLY, TOOLS_ALLOWLIST
  - OPENAI_BASE_URL=https://api.moonshot.ai/v1 (commented for alias compatibility)
- No behavior change until gates are enabled at the end of Batch B

## Restart approach
- I will restart the EXAI-MCP WebSocket daemon via scripts/ws_start.ps1 -Restart as needed
- You will only be asked to restart Augment once at the end when tool visibility (registry) is flipped

## Validation plan
- After each batch, run EXAI-WS validations with unpredictable prompts and capture activity excerpts
- Record outputs under docs/augment_reports/augment_review_02/

