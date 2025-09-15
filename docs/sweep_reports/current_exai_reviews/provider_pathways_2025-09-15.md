MCP Call Summary — Result: YES | Provider: GLM | Model: glm-4.5-flash | Cost: low | Duration: fast | Note: Provider Pathways Inventory generated

# Provider Pathways Inventory and Defaults (Kimi + GLM)

## Purpose
Practical mapping of Kimi and GLM models to everyday workflows with safe defaults, cost control, and clear fallbacks.

## Model mapping (use-cases)
- Fast/flash (default)
  - GLM: glm-4.5-flash (default for most tools)
  - Kimi: k2-turbo / k2-turbo-preview (when explicitly selecting Kimi fast tier)
- Quality/deep (analysis-heavy)
  - GLM: glm-4.5 (non-flash)
  - Kimi: kimi-k2 / kimi-k2-0711 / kimi-k2-0905 (pick the latest stable tag)
- Long-context / thinking
  - Kimi: moonshot-v1-32k or 128k (when long contexts needed), kimi-thinking-preview for experimental deep reasoning
  - GLM: prefer routing with chunking first; only bump model if the tool requires it

## Router hints (suggested)
- DEFAULT_MODEL=glm-4.5-flash
- GLM_FLASH_MODEL=glm-4.5-flash
- GLM_QUALITY_MODEL=glm-4.5
- KIMI_DEFAULT_MODEL=k2-0711-preview (or latest stable k2-####-preview)
- ROUTER_ENABLED=true; EX_ROUTING_PROFILE=balanced

## Thinking mode defaults
- chat/analyze/codereview: thinking_mode=medium (balanced)
- testgen: medium → high when generating complex cases
- thinkdeep: high (bounded by timeouts)

## Websearch defaults
- Provider-native flags can remain enabled, but keep unified defaults conservative:
  - EX_WEBSEARCH_ENABLED=true, EX_WEBSEARCH_DEFAULT_ON=false (opt-in)
  - KIMI_ENABLE_INTERNET_SEARCH=true; GLM_ENABLE_WEB_BROWSING=true
  - Use websearch when: time-sensitive topics, external docs, or user explicitly asks

## Token/cost controls
- Use fast tier first (glm-4.5-flash)
- Increase thinking_mode before changing model tier
- Only bump to quality/long-context if:
  - Chunking still exceeds limits
  - Results show repeated truncation or missing context
- Keep SLIM_SCHEMAS=true for heavy tools

## Fallback strategy (per call)
1) Try flash model + chunking
2) If insufficient: increase thinking_mode (medium → high)
3) If still insufficient: switch to quality model (glm-4.5 or latest kimi-k2)
4) For long files: use chunking + summarize; only escalate to long-context models if essential

## Option B provider consolidation (staged)
- Keep providers/registry_srcshim.py staged but inactive
- Flip at a single import site to src.providers.registry when ready
- Add CI guard to forbid legacy providers.* imports
- Always stamp provider/model in the returned summary for observability

## Minimal environment toggles (recommended)
- LOG_LEVEL=INFO, LOG_FORMAT=json
- EX_ACTIVITY_SUMMARY_AT_TOP=true, EX_ACTIVITY_FORCE_FIRST=true
- STREAM_PROGRESS=true (helps UI)
- EX_HOTRELOAD_ENV=true (tune without restart)
- DEFAULT_USE_ASSISTANT_MODEL=false (avoid surprise costs)
- ENABLE_CONSENSUS_AUTOMODE=false; MIN=1, MAX=2 (if later enabled)

## Quick smoke (per provider)
- GLM fast path: chat_exai-mcp with glm-4.5-flash on a small prompt; confirm cost/time "low/fast"
- Kimi fast path: chat_exai-mcp selecting a k2-turbo variant on similar prompt; compare latency
- Quality bump: analyze_exai-mcp with larger doc; try thinking_mode=high before model bump
- Long-context: same doc; check chunking summaries first, then trial a long-context model if needed

## What to remember
- Default to flash tier; escalate thoughtfully
- Keep websearch opt-in for cost control
- Prefer chunking over long-context unless necessary
- Stamp provider/model in every response for accountability

