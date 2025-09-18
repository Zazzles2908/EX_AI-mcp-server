# Streamlined EXAI‑MCP Usage (Avoid Pitfalls)

This chapter summarizes practical steps to minimize issues (especially with workflow tools like thinkdeep) and keep runs smooth.

## 1) Always send required workflow fields
For multi‑step tools (thinkdeep, planner, analyze, codereview, debug, refactor, tracer, precommit, secaudit):
- Required: step, step_number, total_steps, next_step_required, findings
- Recommendation: adopt a small client helper/wrapper that auto‑fills these fields and increments step_number.

## 2) Batch responsibly
- Prefer small batches (≤3 concurrent calls). If any call mis‑shapes, you can retry quickly.
- Keep related edits/analyses sequential to preserve context and reduce cross‑noise in logs.

## 3) Preflight parameter validation (client‑side)
- Add a tiny preflight check before calling EXAI‑MCP:
  - If tool is workflow‑type and findings is missing → inject a default like "Kickoff".
  - If step_number/total_steps missing → assume 1/1 and set next_step_required=false.
  - If model omitted → set model="auto" to engage routing.

## 4) Use routing hints explicitly when you care
- Long context: add estimated_tokens or include the full prompt chunk so the router sees it.
- Web/time sensitive: set use_websearch=true or include a URL/time phrase.
- Vision: include modality cues if supported.

## 5) Observe MCP_CALL_SUMMARY
- mcp_activity.log shows the chosen model, token estimate, and duration. Treat this as your source of truth for what happened.
- If routing surprises you, confirm hints and thresholds (see Routing chapter).

## 6) Encoding & platform tips (Windows)
- Prefer plain UTF‑8 text. Avoid pasting content with hidden control characters.
- Use PowerShell `Get-Content -Tail -Wait` to follow logs; prefer ASCII in config/doc files.

## 7) Retry/backoff
- For transient provider/network errors, retry with exponential backoff. Keep idempotency where possible.

## 8) Idempotent continuation
- For multi‑step runs, set a stable continuation_id (if your client supports it) so runs remain thread‑safe.

## 9) Optional future toggles
- Hard‑prefer Kimi/Moonshot for long_context via an env toggle, when long context is critical and latency is acceptable.

## 10) Smoke early, smoke often
- After any env/router change, run `python tools/ws_daemon_smoke.py` to re‑validate streaming, web‑cue, and long‑context paths.

