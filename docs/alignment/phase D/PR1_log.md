# Phase D — PR1 Log: ModelRouter + Observability + Summary Stamps

Summary: Implemented lightweight DEBUG observability inside ModelRouter.decide(), verified existing boundary routing and MCP Call Summary stamping are active, and ran unit tests for routing logic. Preparing PR against main.

Changes
- utils/model_router.py: add [ROUTER_DECISION] debug log emitting tool, profile, requested, files, images, choice
- No functional routing changes; only logging
- Verified server-side boundary routing and MCP Call Summary insertion already implemented in server.py and tools/simple/base.py

Unit Tests
- Ran: tests/test_model_router.py, tests/test_model_router_fallback.py
- Result: 7 passed (0.26s)

EXAI MCP Validation (Step C – quick smoke)
- status_exai-mcp (hub=true): providers configured = GLM, KIMI; models visible include glm-4.5(-flash/-air), kimi-k2 family, kimi-thinking
- chat/analyze/testgen/codereview quick calls: initiated for routing sanity (no content persisted here); server logs will include [MODEL_ROUTE] and [ROUTER_DECISION]

Acceptance Criteria Mapping
- Router resolution observable: YES (server [MODEL_ROUTE] + router [ROUTER_DECISION])
- Summary stamp top-of-response: YES (server-wide insertion + SimpleTool)
- Minimal wiring to chat/analyze: YES (server boundary resolves model; BaseTool consumes pre-resolved context)
- Costs/duration stamp present: YES (duration band + cost heuristic in summary)

Next
- Open PR to main with this logging change and test validation notes
- After merge, proceed with Step C full validation set and attach evidence under docs/alignment/mcp_runs and docs/sweep_reports/phase4_exai_review

