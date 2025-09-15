MCP Call Summary — YES | Provider: N/A | Model: N/A | Cost: none | Duration: fast

Title: Server-level MCP Call Summary injection for all tools
Date: 2025-09-15
Branch: chore/docs-sweep-and-layering

What changed
- server.py: handle_call_tool now prepends a compact "MCP Call Summary — …" one-liner to every tool result
- Includes: Result (YES/NO), Provider, Model, Cost (heuristic), Duration (fast/moderate/slow)
- Skips insertion when the first block already starts with "MCP Call Summary —" (avoids duplication for SimpleTool tools)
- Measures duration at request start and computes label after execution (includes auto-continue time)

Why this approach
- Centralized injection guarantees consistent UX across SimpleTool and workflow tools without touching each tool’s code
- Preserves existing JSON payload as the next block
- Compatible with the existing optional Activity summary lines in server

Key logic (high level)
- Start timer at entry to handle_call_tool
- After tool execution, normalize result and perform auto-continue as configured
- Prepend the MCP summary line unless it already exists
- Provider/model pulled from resolved model and provider; cost is a simple heuristic; result derived from JSON status when available

Impact
- All tools will show the summary as the first TextContent block after server restart
- SimpleTool-based tools keep their own summary; server detects and does not duplicate

Action required
- Restart EXAI MCP server to load server.py changes

Follow-up
- After restart, run extended pathway smokes and capture consolidated results with the new summary in docs/alignment/mcp_runs/
- Consider a tiny CI grep to ensure the summary line exists in outputs

