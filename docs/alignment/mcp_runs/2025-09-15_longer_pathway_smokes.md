# 2025-09-15 — Longer Pathway Smokes (GLM + Kimi)

Result: PARTIAL YES — Summary line live on success paths; error-path coverage added and requires one more server restart to activate uniformly.

## Environment snapshot
- Providers configured: GLM, Kimi (from status tool)
- Models visible (subset): glm-4.5, glm-4.5-air, glm-4.5-flash; kimi-k2-0711, kimi-k2-0905, kimi-k2-turbo; kimi-thinking-preview
- Tools loaded: analyze, chat, codereview, debug, planner, refactor, status, testgen, thinkdeep

## What changed in this run
- SimpleTool now prepends a compact MCP Call Summary line on success paths:
  - Format: "MCP Call Summary — Result: YES|NO | Provider: <name> | Model: <id> | Cost: low|medium|high | Duration: fast|moderate|slow"
  - The original JSON ToolOutput follows as the next TextContent block, unchanged
- Additional update (pending restart): prepend the same summary on common error paths
  - Invalid file path errors
  - Provider returned None
  - Response blocked/incomplete (finish_reason)
  - MCP size-check rejections
  - Generic exception fallback

## Smokes executed (high level)
- status: Verified providers/models/tools availability
- chat (GLM): attempted with large files → size guard triggered; re-run without files (OK)
- chat (Kimi): attempted with file → size guard triggered; re-run without files (OK)
- codereview/testgen: step-1 kickoffs to exercise workflow tools (OK)

Note: The success-path responses now include the new one-liner summary. Uniform error-path summaries will appear after the next restart (change already applied locally).

## Next actions
1) Restart server once more to activate error-path summary prepends
2) Re-run extended smokes across tools (chat/analyze/codereview/testgen/refactor) and capture a consolidated batch in this folder
3) Push commits after Git auth is corrected (GH_TOKEN/GITHUB_TOKEN cleanup or switch to SSH)

## Safety/compatibility
- No change to the JSON ToolOutput contract or metadata structure
- Summary is an additional first TextContent only; downstream parsers remain unaffected

