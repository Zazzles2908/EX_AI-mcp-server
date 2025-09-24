# P4 Batch 4 — Advisory Hints + Validation (with/without manager)

- YES — Completed advisory-hints scaffold, env flags, restarts, and A/B validations. Real model outputs shown; advisory plan logs captured only when enabled.

## Env states tested
1) Manager OFF, Advisory ON
   - EX_AI_MANAGER_ENABLED=false
   - EX_AI_MANAGER_ADVISORY=true
2) Manager ON, Advisory ON
   - EX_AI_MANAGER_ENABLED=true
   - EX_AI_MANAGER_ADVISORY=true

## A) Manager OFF (baseline)
- Restart: OK (no AI Manager init logs)
- Outputs (real models):
  - GLM chat (glm-4.5-flash): sand-otter-1a2c
  - Kimi multi-file chat (kimi-k2-0905-preview): aqua-wasp-9d71
- Activity log: no `ai_manager_plan` entries (expected)

## B) Manager ON (advisory only)
- Restart: OK; logs include:
  - AI Manager scaffold enabled (strategy=manager-first) — no routing changes yet
  - AI Manager initialized (scaffold) — no routing changes yet
- Outputs (real models):
  - GLM chat (glm-4.5-flash): blue-marten-6f22
  - Kimi multi-file chat (kimi-k2-0905-preview): silver-yak-4c8d
- Advisory plan logs (mcp_activity):
  - chat → suggested_provider=glm, suggested_model=glm-4.5-flash, has_files=false
  - kimi_multi_file_chat → suggested_provider=kimi, suggested_model=kimi-k2-0905-preview, has_files=true

## Conclusions
- Behavior unchanged (no routing changes) in both states; only additional advisory logs when enabled.
- Real provider outputs confirm no hardcoded responses.
- The Mermaid diagram in ai_manager_decision_tree_2025-09-24.md renders after sanitization.

## Next steps
- Optional: keep EX_AI_MANAGER_ENABLED=true and EX_AI_MANAGER_ADVISORY=true for ongoing plan logging, or set back to false to reduce logs.
- Proceed to P4 Batch 5 (if desired): minimal unit-style checks for plan object shape (no external deps), then draft manager integration toggles proposal.

