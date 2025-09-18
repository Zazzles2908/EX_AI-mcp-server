# Phase E Implementation Plan (Maps to External Review Phase 1)

One-line YES/NO: YES — This plan completes Phase 1 foundations with minimal risk, clear sequencing, and verifiable success criteria.

EXAI-MCP summary: provider=GLM (glm-4.5-flash) primary, Kimi selective; cost=$0 for planning; total call time≈instant

## Objectives and Outcomes
- Restore consensus tool reliability and assessment parsing
- Establish platform integrations (Moonshot+Z.ai) with unified auth and health checks
- Add task routing + basic 256K-aware context management + streaming scaffolds
- Validate via comprehensive tests (functionality, security, performance, UX proxy)

## Scope (Phase 1.1–1.4)
- 1.1 Critical Repairs: Pydantic schema, JSON parsing fallback, secure path validation
- 1.2 Platform Integration: HybridPlatformManager (auth, rotation, health), error framework
- 1.3 Core Refactor: IntelligentTaskRouter (MVP), AdvancedContextManager (MVP, 256K-aware), streaming stub
- 1.4 Testing & Validation: System tests, security audit battery, baselines/benchmarks, quick UAT proxy

## Deliverables
- tools/consensus/: fixed models and parsing fallback; unit tests
- providers/hybrid_platform_manager.py: unified Moonshot/Z.ai auth + health
- routing/task_router.py: capability-based routing MVP
- context/context_manager.py: token budgeting + truncation MVP (256K aware)
- streaming/streaming_adapter.py: interface + no-op adapters
- tests/: unit + integration + security/path tests; benchmarks scripts
- docs/alignment/phase E/: Implementation_Plan.md, Implementation_Checklist.md

## Work Packages and Sequencing
1) P1.1 Consensus and Security (Week 1)
- Fix Pydantic model (ConsensusRequest.requires findings: List[str])
- Add assessment parsing fallback; robust JSON error handling
- Central secure path validation (prevent traversal, absolute injection); expandable allowlist
- Unit tests for schema, parsing, and path sanitizer

2) P1.2 Platform Integrations (Week 2)
- Implement HybridPlatformManager with unified auth (env-based), key rotation hooks
- Health checks (Moonshot and Z.ai) + connectivity tests
- Error handling framework: retries, backoff, failure classification; INFO logs

3) P1.3 Core Architecture (Week 3)
- IntelligentTaskRouter MVP: classify by capability/context length; route accordingly
- AdvancedContextManager MVP: token estimator, system+recent preservation, middle summarization placeholder
- Streaming adapter interfaces; stubs per platform (no functional UI yet)

4) P1.4 Validation (Week 4)
- System tests: consensus/platforms/routing/context suites
- Security tests: injection/traversal/DOS-lite; path sanitizer cases
- Performance baselines: consensus 100 iterations, routing/context micro-bench
- Quick UX proxy: CLI flows emulate beginner vs advanced (progressive disclosure placeholder)

## Success Criteria (per external prompt)
- Consensus tool 100% restored; JSON parsing >95% success
- 0 critical path-handling vulnerabilities (tests)
- Both platforms connected/authenticated; health<=1s; error framework catches/logs
- Context manager handles 256K without errors; routing accuracy ≥90% on test set
- Streaming interface in place (latency target <100ms placeholder, validated later)

## Dependencies & Prereqs
- .env keys for Moonshot and Z.ai; SecureInputValidator enablement
- Existing EXAI WS keepalive/micro-steps remain unchanged

## Risks and Mitigations
- Over-scoping router/context: keep MVP; iterate later
- Flaky platform SDKs: health checks, retries, fallbacks
- Security gaps: enforce sanitizer tests; fail closed by default

## Verification Plan
- Pytest suites (unit/integration), security tests, smoke health checks
- Benchmarks recorded to docs/sweep_reports with run IDs
- EXAI-MCP simulator quick runs to verify workflows unaffected

## Rollout
- Land code and tests -> run full Phase 1.4 battery -> documentation updates -> PR

