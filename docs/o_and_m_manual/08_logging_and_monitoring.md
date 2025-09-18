# Logging & Monitoring

## Files
- logs/mcp_server.log — detailed server diagnostics
- logs/mcp_activity.log — tool calls and compact summaries

## Watch live (Windows PowerShell)
```
Get-Content -Path logs\mcp_activity.log -Tail 200 -Wait
Get-Content -Path logs\mcp_server.log -Tail 200 -Wait
```

## Common patterns
- TOOL_CALL — tool name, request id, brief args
- TOOL_COMPLETED — completion marker with status
- MCP_CALL_SUMMARY — model, tokens, duration (primary ops signal)

Example
```
MCP_CALL_SUMMARY: tool=thinkdeep status=COMPLETE step=1/1 dur=0.6s model=kimi-thinking-preview tokens~=1107 ...
MCP_CALL_SUMMARY: tool=chat status=COMPLETE dur=0.2s model=glm-4.5-flash tokens~=303 ...
```

## Quick triage queries
PowerShell
```
Select-String -Path logs\mcp_activity.log -Pattern "MCP_CALL_SUMMARY"
Select-String -Path logs\mcp_server.log -Pattern "ERROR|Traceback"
```
Bash
```
grep MCP_CALL_SUMMARY logs/mcp_activity.log
grep -E "ERROR|Traceback" logs/mcp_server.log
```

## What to watch
- Repeated provider errors (auth, rate limit)
- Model selections diverging from expectations (compare with Routing doc)
- Large durations on simple tools (network/provider check)

