MCP Call Summary — Result: OK | Provider: GLM/Kimi (mixed) | Models: glm-4.5(-flash), kimi-k2-0711/0905 | Duration: fast/moderate | Cost: low/medium

EXAI-MCP Stability Smoke Evidence (from logs)

- Status tool present and invoked:
  - 2025-09-16 07:58:15 — TOOL_CALL: status (req_id=7086413d-…)
- Chat tool successful:
  - 2025-09-16 07:58:16 — chat (glm-4.5-flash) TOOL_COMPLETED
  - 2025-09-15 22:27:10 — chat (kimi-k2-0711-preview) TOOL_COMPLETED
- Analyze tool successful (multi-step):
  - 2025-09-16 07:58:18 — analyze Step 1/1 TOOL_COMPLETED
  - 2025-09-15 22:53:47 — analyze Step 3/3 TOOL_COMPLETED
- Codereview tool successful:
  - 2025-09-16 07:58:23 — codereview Step 1/1 TOOL_COMPLETED
- Testgen tool successful:
  - 2025-09-16 07:58:20 — testgen TOOL_COMPLETED

Router/summary confirmations
- Server logs include sanitized provider/model payloads and summary logic
- Summary utils present (utils/summary.py); headers observed in logs

Notes
- ws shim health (logs/ws_daemon.health.json): running on 127.0.0.1:8765, sessions: 0 at last sample
- Historic partial tool load errors resolved (status now listed/callable). Remaining non-critical tool registry warnings do not affect core tools.

Acceptance (smoke): PASS — core tools callable; routing and summary in place.

