# Import Shims Matrix (Providers)

Purpose: Document temporary import redirections to ensure one canonical codepath

Top-level → Canonical mapping
- providers.base → src.providers.base
- providers.openai_compatible → src.providers.openai_compatible
- providers.glm → src.providers.glm
- providers.kimi → src.providers.kimi
- providers.zhipu_optional → src.providers.zhipu_optional
- providers.moonshot → src.providers.moonshot
- providers.zhipu → src.providers.zhipu
- providers.registry → src.providers.registry
- providers.custom → src.providers.custom
- providers.openrouter → src.providers.openrouter
- providers.openrouter_registry → src.providers.openrouter_registry
- providers.capabilities → src.providers.capabilities
- providers.metadata → src.providers.metadata

Mechanism
- providers/__init__.py pre-populates sys.modules for the above entries
- Behavior is read-only; implementations live under src/providers

Removal
- After Phase F (post-green window), remove top-level providers/* and the shims

