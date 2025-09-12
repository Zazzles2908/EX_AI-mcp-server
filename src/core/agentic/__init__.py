"""
Agentic engine scaffolding package.

Implements initial, non-invasive interfaces for:
- HybridPlatformManager (Moonshot + Z.ai)
- IntelligentTaskRouter (capability/context/multimodal-aware)
- AdvancedContextManager (256K-aware context optimization)
- ResilientErrorHandler (retry/backoff/fallbacks)
- SecureInputValidator (centralized path/image validation)

All integration is gated by feature flags in config.py and is OFF by default.
"""

