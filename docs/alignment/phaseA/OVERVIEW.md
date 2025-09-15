# Phase A Alignment Overview (Draft)

This document captures the minimal, low-risk alignment steps to reduce complexity while preserving the design intent, anchored to:
- docs/architecture/advanced_context_manager/
- docs/architecture/toolkit/

Focus: establish clear defaults (env guardrails), consolidate documentation sources, and make script entry-points obvious without removing functionality.

## Goals
- Canonicalize configuration with a clean .env (minimal) and an explanatory .env.example (detailed) — done.
- Keep GLM 4.5 Flash as the manager/primary executor for cost/latency balance.
- Enable cost-aware routing (router) with a balanced profile.
- Disable second-pass expert analysis by default to avoid surprise costs.
- Provide a transparent map of superseded scripts and their preferred replacements.

## Guardrail Defaults (applied in .env)
- DEFAULT_MODEL=glm-4.5-flash
- ROUTER_ENABLED=true, EX_ROUTING_PROFILE=balanced
- EXPERT_ANALYSIS_MODE=disabled, DEFAULT_USE_ASSISTANT_MODEL=false
- UI_PROFILE=compact, SLIM_SCHEMAS=true
- ENABLE_CONSENSUS_AUTOMODE=false, MIN_CONSENSUS_MODELS=1, MAX_CONSENSUS_MODELS=2
- SECURE_INPUTS_ENFORCED=true, CHUNKED_READER_ENABLED=true
- POLICY_EXACT_TOOLSET=true

These align the runtime with an agentic manager (GLM 4.5 Flash) that is cost-aware, low-latency, and safe by default.

## Documentation Canonicalization
- Canonical technical direction: docs/architecture/* (advanced_context_manager, toolkit)
- Legacy external review prompts remain for historical context; new alignment notes will live under docs/alignment/phaseA/*

## Next Steps
- Review SCRIPTS_SUPERSESSION.md and confirm the recommended primary entry-points.
- After confirmation, we can add deprecation banners into legacy scripts and simplify the scripts/ tree.
- Plan provider consolidation (Phase B) and packaging/entry points (Phase C).

