# Routing & Decision Paths

## Signals the router considers
- Web/time cues: use_websearch=true, presence of http(s) URLs, words like "today", "latest"
- Context size: estimated_tokens (explicit) or prompt-length estimate (~4 chars per token)
- Modality: images/vision keywords if the tool requests it
- Env preferences: WORKFLOWS_PREFER_KIMI and other toggles

## Selection algorithm (current defaults)
1) If web/time cue present: prefer GLM browsing path
2) Else if estimated_tokens > 128k: choose Kimi/Moonshot (very long context)
3) Else if estimated_tokens > 48k: bias to Kimi/Moonshot (long context)
4) Else if vision/multimodal cues present: prefer GLM (configurable)
5) Else: default to GLM (glm-4.5-flash) for speed

## Dispatch hints from tools
- Tools may add routing hints before provider selection:
  - long_context
  - estimated_tokens:<n>
- Provider fallback chain sorts by context_window and long-context preference when hints are present.

## Configuration knobs
- DEFAULT_MODEL=auto (enable agentic routing)
- WORKFLOWS_PREFER_KIMI=true (increase bias toward Kimi/Moonshot for long-context)
- Optional hard-preference toggle (future): always route long_context to Kimi/Moonshot

## Practical playbook
- Want Kimi for a giant one-shot prompt? Include full text in prompt/messages or pass estimated_tokens; keep model=auto.
- Want GLM for browsing? Use use_websearch=true or include a URL/time phrase.
- Measuring behavior: read MCP_CALL_SUMMARY in logs/mcp_activity.log to see final model and tokens.

## Why a route may not trigger
- Upstream shaping trimmed the prompt so estimated_tokens fell below threshold
- GLM context window was sufficient and latency preference kept GLM first
- Missing required workflow fields (e.g., thinkdeep findings) caused early validation failures

## Examples
- Long-context research:
  - chat with model=auto and a very large prompt (or estimated_tokens=120000) 2 Kimi/Moonshot
- Time-sensitive web query:
  - thinkdeep with use_websearch=true and a URL 2 GLM browsing path

