# Decision-Tree Architecture Overview (Beta Phase)

This document summarizes the high-level decision tree used by the manager to route
requests across tools and providers.

Top-level flow:
- If trivial prompt: answer directly with GLM-4.5-flash.
- Else: Planner selects the appropriate tool (analyze/codereview/debug/...).
- For file-heavy tasks: upload/extract then pass to the chosen tool.
- For Kimi/GLM chat with tools: use provider-native tool loops; fall back to chat.

Telemetry & Circuit Breakers:
- All provider failures emit standardized envelopes.
- Circuit breakers track per-provider failures and cool-off periods.

Next steps:
- Add Mermaid diagrams and attach the orchestrator/circuit modules.

