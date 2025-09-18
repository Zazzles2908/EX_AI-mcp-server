# Providers & Models

## Overview
The system integrates GLM (Zhipu) and Kimi/Moonshot. The router selects the best model per request using cues (web, long-context, vision), token estimates, and environment preferences.

## GLM (Zhipu)
- Strengths: low latency, strong web/browse path, solid baseline quality
- Recommended default: glm-4.5-flash (fast manager)
- Good for: everyday prompts, web/time-sensitive queries, multimodal/vision (variant dependent)
- Context window: large enough for most tasks

## Kimi / Moonshot
- Strengths: long-context, deep reasoning, high quality
- Good for: very large prompts, multi-document analysis, deep reviews
- Context window: very large; preferred when long_context is signaled

## Streaming & Web
- Streaming: validate with `stream_demo` (stream=true)
- Web/time cues: use thinkdeep or chat with `use_websearch=true` or include a URL/time phrase; router will bias to the provider with the stronger browsing path

## Custom/OpenAI-compatible providers
- Configure `CUSTOM_API_URL` and `CUSTOM_API_KEY` to route through a local or 3rd-party OpenAI-compatible endpoint

## Inspecting availability/capabilities
- listmodels: shows visible models for current keys
- provider_capabilities: includes context_window and features when available

## Selection guidance (practical)
- Prefer GLM when: speed matters, prompt fits comfortably, browsing needed
- Prefer Kimi/Moonshot when: prompt is very large (estimated_tokens > 48k), deep analysis, high-quality outputs favored

## Environment variables to know
- KIMI_API_KEY, GLM_API_KEY, CUSTOM_API_URL, CUSTOM_API_KEY
- WORKFLOWS_PREFER_KIMI=true biases the long-context order

## Future adjustments
- Optional hard-preference toggle for long_context
- Cost/latency-aware routing (e.g., prefer GLM under strict latency budgets)

