# Upgrades & Future Adjustments

## Current state
- GLM as fast manager; long-context bias toward Kimi/Moonshot
- Async streaming stable; dispatch metadata includes estimated_tokens/long_context

## Roadmap (examples)
- Hard-preference toggle for long_context (env-gated)
- Cost/latency-aware routing (SLA/budget hints)
- Provider-native tokenizer for better size estimates
- Expanded provider matrix; explicit vision routing rules

## Release flow (safe pattern)
1) Branch off `main`
2) Run quality checks + smoke tests
3) Add/adjust env toggles; document in O&M manual
4) Implement changes; add unit tests where applicable
5) Run simulator tests (quick + targeted)
6) Review logs; update sweep reports
7) Merge after green

## Documentation touchpoints
- 06_routing_and_decision_paths.md — update policy changes
- 04_providers_and_models.md — add new providers/models
- sweep_reports/phase4_exai_review — append validation evidence

