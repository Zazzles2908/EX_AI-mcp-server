# Troubleshooting

## Quick decision trees (common cases)

1) No tools appear in client
- Check LEAN_MODE/LEAN_TOOLS/DISABLED_TOOLS in .env
- Verify server logs show the tool registry at startup (mcp_server.log)

2) Provider 401/403 or model not found
- Verify KIMI_API_KEY / GLM_API_KEY; re-run `listmodels`
- Check mcp_server.log for provider init errors

3) Unexpected model selection
- Confirm long_context/estimated_tokens hints; if missing, router may keep GLM
- If prompt is trimmed upstream, effective size may drop below threshold

4) Streaming error (“event loop already running”)
- Use stream_demo (async streaming path is implemented); re-run smoke script

5) Web cue didn’t trigger
- Set use_websearch=true or include an https:// URL / time phrase
- Inspect MCP_CALL_SUMMARY for the actual model path

6) Validation errors on multi-step tools (thinkdeep/planner)
- Always include: step, step_number, total_steps, next_step_required, findings

## Self-checks
- Logs: mcp_activity.log for summaries; mcp_server.log for exceptions
- Configuration: `.env` values match desired behavior; restart server after changes
- Smoke: `python tools/ws_daemon_smoke.py` confirms streaming/web/long-context paths

