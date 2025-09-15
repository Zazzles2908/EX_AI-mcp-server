# EX MCP Server — Architecture Map (Current State)

This document maps key modules, their responsibilities, and how they connect. It also highlights apparent duplication and consolidation targets.

## High-level layers
- Entry points:
  - server.py (MCP server), remote_server.py (remote), scripts/run_ws_daemon.py (WS daemon)
- Tools (MCP tools exposed to clients):
  - tools/*.py (primary), tools/workflow/* (workflow mixins, final-step logic), tools/shared/* (shared base)
- Providers (LLM backends):
  - Top-level providers/* (current active provider impls used by tools)
  - src/providers/* (legacy/newer refactor layer; overlapping content exists)
- Utilities / Core support:
  - utils/* (file IO, chunking, storage, routing, costs, http, config, etc.)
  - systemprompts/* (system prompts per tool)
  - src/core, src/router, src/embeddings (framework/refactor modules)

## Tool flow (end-to-end)
1) Client calls an MCP tool (e.g., analyze/codereview/debug)
2) Tool validates args via utils/request_validation.py
3) Tool uses tools/shared/base_tool.py for shared behaviors:
   - Model resolution (via boundary and utils/model_router.py)
   - File expansion and secure input validation (utils/secure_inputs.py)
   - Chunked reader on final step (utils/file_chunker.py)
   - Token budget (utils/model_context.py)
4) Tool delegates final expert call through provider registry:
   - providers/registry.py (top-level) selects concrete provider (GLM/Kimi/...)
   - provider impl (e.g., providers/glm.py or providers/kimi.py) executes API
5) Deferred results path (tools/workflow/workflow_mixin.py):
   - Starts background task, returns handle
   - Emits heartbeats and proactive fallback if slow
   - Completes with provider and elapsed info

## Providers (current active)
- providers/registry.py — central registry
- providers/glm.py — GLM implementation (top-level)
- providers/kimi.py — Moonshot/Kimi implementation (top-level)
- providers/openai_compatible.py — shim for OpenAI-compatible endpoints
- providers/zhipu_optional.py + providers/zhipu/* — optional Zhipu SDK integration

NOTE: src/providers/* contains a parallel provider stack (base, glm, kimi, registry, etc.). The running code primarily imports from top-level providers/*, but some utilities (e.g., utils.model_router) reference src.providers.* in places. This creates duplication and risk of divergence.

### Provider connection points
- Tools resolve model -> provider via providers/registry.py
- Provider implementations use utils/http_client.py to POST/GET
- Timeouts/retry/backoff configured at provider + http client layer

## Utilities (key modules and connections)
- utils/model_router.py — routing, cost-aware fallbacks, Kimi selector
- utils/file_chunker.py — chunked read windows for final step
- utils/secure_inputs.py — file size/extension/binary guardrails
- utils/model_context.py — token allocation, budgets
- utils/http_client.py — httpx client wrapper with per-provider timeouts
- utils/storage_backend.py — in-memory deferred storage
- utils/conversation_memory.py — conversation turns storage

## Workflows and prompts
- tools/workflow/workflow_mixin.py — final-step embedding + deferred logic, proactive fallback
- systemprompts/* — system prompts for each tool

## Apparent duplication and risks
- providers vs src/providers
  - Both contain base/registry/provider impls (glm/kimi/openai compatible/zhipu)
  - Some new code (e.g., utils.model_router) references src.providers types
  - Active tools import top-level providers; mixing layers risks subtle bugs
- tools vs src/tools
  - src/tools only contains __init__.py currently (placeholder for refactor). The actual tools live under tools/*

## Consolidation proposal (phased)
1) Single source of truth for providers
   - Option A (recommended): migrate references to use src/providers/* exclusively; move top-level providers/* into src/providers and update imports
   - Option B: keep top-level providers/* as the canonical location; remove src/providers duplicates and redirect imports
   - Whichever we choose, add a static check to prevent mixed imports across layers
2) Unify registry import path
   - Ensure all call sites import from a single registry module (e.g., providers.registry)
   - Update utils/model_router.py to consistently import ProviderType from the chosen path
3) Mark legacy modules with clear headers and deprecation warnings
   - Add module-level warnings for legacy files during the transition window

## Decisions queued (record of recent changes to not forget)
- Deferred results ON for reliability: EXPERT_DEFERRED_RESULTS=true
- Proactive fallback at 12s: EXPERT_FALLBACK_AFTER_SECS=12
- Time budget 90s: EXPERT_TIME_BUDGET_SECS=90
- Cost-aware fallback order adjusted (cheapest-first):
  - GLM -> Kimi: kimi-k2-0711-preview, kimi-k2-0905-preview, kimi-latest (code tools bias 0905)
  - Kimi -> GLM: glm-4.5-air, glm-4.5-flash, glm-4.5
- Kimi model selector defaults (no turbo by default):
  - Simple/general: k2-0711-preview; Code: k2-0905-preview; Creative/Long: kimi-latest
- HTTP timeouts per provider (env-driven):
  - GLM_HTTP_TIMEOUT_CONNECT/READ/WRITE/POOL
  - Default fallback: HTTP_TIMEOUT_CONNECT/READ/WRITE/POOL
- WS handshake noise reduced
- Secure inputs validation added in BaseTool
- Chunked reader enforced for final step embedding

## Next steps I will execute (with your go-ahead)
- Pick a single provider layer and refactor imports to it (recommended: src/providers as canonical)
- Replace mixed imports: utils.model_router and tools/workflow to import ProviderType/registry from the canonical module only
- Add a lightweight CI check (e.g., a test) that rejects mixed-layer provider imports
- Update README docs and developer guide to reflect the canonical provider path, env timeouts, and fallback ordering

