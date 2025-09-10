# EX MCP Model Selection — What happens per tool

This is a concise, practical map of which model gets used when you call each EX MCP tool and why.

## Global rules (server-side)
- Default model: `DEFAULT_MODEL` from config (currently `glm-4.5-flash`).
- Caller can pass `model` or `model:option` (e.g., `glm-4.5:beta`).
- If `model` = `auto`, server resolves it via `resolve_auto_model()`:
  - If locale is zh-* or user text contains CJK → prefer Kimi (`KIMI_DEFAULT_MODEL` or `KIMI_QUALITY_MODEL`).
  - If `local_only=true` and CUSTOM provider exists → use `CUSTOM_MODEL_NAME`.
  - Else if GLM exists → `glm-4.5-flash`.
  - Else → provider fallback for the tool’s category (Extended Reasoning vs Fast).
- All tools that `require_model()` get the model resolved at the MCP boundary, and a ModelContext is passed in.
- Progress is attached both to `metadata.progress` and inlined into the same text as `=== PROGRESS ===`.

## Special cases
- thinkdeep: If `THINK_ROUTING_ENABLED` and caller didn’t specify a concrete model (missing or `auto`), server picks:
  - Kimi available → `kimi-k2-thinking`
  - Else GLM available → `glm-4.5`
  - Else → returns guidance to configure KIMI or GLM or pass an explicit model.
- consensus: Does not take a single model; when `models` not provided and `ENABLE_CONSENSUS_AUTOMODE=true`, server auto-selects a list:
  - Uses `MIN_CONSENSUS_MODELS`/`MAX_CONSENSUS_MODELS` (default 2..3)
  - Prefers env `GLM_QUALITY_MODEL`/`KIMI_QUALITY_MODEL`, then speed models, then provider-priority pool

## Tool-by-tool

- chat (SimpleTool, requires model)
  - Model: explicit `model` → used; else `DEFAULT_MODEL` (or resolved if `auto`).
  - Provider fallback chain is enabled; metadata includes `model_used` and `provider_used`.

- analyze (WorkflowTool, requires model)
  - Model resolved at server; category = Extended Reasoning → auto prefers Kimi/GLM quality tier.

- codereview (WorkflowTool, requires model)
  - Same as analyze; Extended Reasoning category.

- debug (WorkflowTool, requires model)
  - Same as analyze; Extended Reasoning category.

- refactor (WorkflowTool, requires model)
  - Same as analyze; Extended Reasoning category.

- precommit (WorkflowTool, requires model)
  - Same as analyze; Extended Reasoning category.

- secaudit (WorkflowTool, requires model)
  - Same as analyze; Extended Reasoning category.

- testgen (WorkflowTool, requires model)
  - Same as analyze; Extended Reasoning category.

- thinkdeep (WorkflowTool, requires model)
  - Special routing described above; chooses a thinking-tuned model when possible.

- planner (WorkflowTool, does NOT require model)
  - Runs entirely without model resolution at the boundary. Uses workflow semantics; no model call.

- tracer (WorkflowTool, does NOT require model)
  - Same: no model resolution at boundary; no model call by default.

- docgen (WorkflowTool, does NOT require model)
  - Same: no model resolution at boundary; no model call by default.

- consensus (WorkflowTool, multi-model)
  - If `models` passed, uses them; if not, autoselects per the special case above.

## Environment variables you can tune
- DEFAULT_MODEL: fallback model when none provided (string or `auto`).
- THINK_ROUTING_ENABLED: enable special routing for thinkdeep (default true).
- ENABLE_INTELLIGENT_SELECTION: enable category-aware auto selection (default true).
- GLM_QUALITY_MODEL / GLM_SPEED_MODEL: influence quality vs speed picks.
- KIMI_QUALITY_MODEL / KIMI_SPEED_MODEL / KIMI_DEFAULT_MODEL: same for Kimi.
- ENABLE_CONSENSUS_AUTOMODE, MIN_CONSENSUS_MODELS, MAX_CONSENSUS_MODELS: control consensus auto-selection.
- CUSTOM_API_URL, CUSTOM_MODEL_NAME: for local models when `local_only` or explicit `model` uses custom provider.

## Quick mental model
1) You call a tool → server decides whether a model is required.
2) If model is needed: resolve explicit model or auto using rules above.
3) For thinkdeep/consensus, apply their special selection.
4) Tool runs with a ModelContext and returns output with progress and metadata (including the model used for SimpleTools).

