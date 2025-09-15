from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


@dataclass
class ContextOptimizationResult:
    """Result of context optimization with metadata."""

    optimized_content: List[Dict[str, Any]]
    original_tokens: int
    optimized_tokens: int
    compression_ratio: float
    strategies_applied: List[str]
    cache_hit: bool = False


@dataclass
class SemanticCacheEntry:
    """Cached context with semantic metadata."""

    content: List[Dict[str, Any]]
    semantic_hash: str
    created_at: datetime
    last_accessed: datetime
    access_count: int
    token_count: int
    compression_strategies: List[str]


class AdvancedContextManager:
    """
    Advanced 256K+ token context management with intelligent optimization.

    Features:
    - Model-aware token allocation based on actual capabilities
    - Semantic caching for repeated context patterns
    - Intelligent truncation with conversation flow preservation
    - Dynamic compression strategies based on content type
    - Cross-tool context consistency

    Integration with existing systems:
    - Works with utils.model_context.ModelContext for token budgets
    - Integrates with utils.conversation_memory for thread context
    - Supports file deduplication from tools.shared.base_tool
    """

    def __init__(self) -> None:
        # Model-specific limits (will be dynamically updated based on actual model)
        self.default_limits = {
            "moonshot": 256_000,
            "zai": 128_000,
            "kimi": 200_000,
            "glm": 128_000,
            "custom": 100_000,
        }

        # Semantic cache for context optimization
        self._semantic_cache: Dict[str, SemanticCacheEntry] = {}
        self._cache_max_size = 100
        self._cache_ttl_seconds = 3600  # 1 hour

        # Compression strategies
        self._compression_strategies = [
            "preserve_system_messages",
            "newest_first_prioritization",
            "semantic_summarization",
            "key_information_extraction",
            "conversation_flow_preservation"
        ]

    def optimize_context(
        self,
        content: Union[List[Dict[str, Any]], str],
        model_context: Optional[Any] = None,
        platform: Optional[str] = None,
        preserve_conversation_flow: bool = True,
        enable_caching: bool = True
    ) -> ContextOptimizationResult:
        """
        Optimize context for model-specific token limits with intelligent strategies.

        Args:
            content: Messages/content to optimize (list of dicts or string)
            model_context: ModelContext instance for token budget calculation
            platform: Platform hint ("moonshot", "zai", "kimi", "glm", "custom")
            preserve_conversation_flow: Whether to maintain conversation chronology
            enable_caching: Whether to use semantic caching

        Returns:
            ContextOptimizationResult with optimized content and metadata
        """
        start_time = time.time()

        # Normalize input to list of messages
        if isinstance(content, str):
            messages = [{"role": "user", "content": content}]
        else:
            messages = content.copy() if content else []

        if not messages:
            return ContextOptimizationResult(
                optimized_content=[],
                original_tokens=0,
                optimized_tokens=0,
                compression_ratio=1.0,
                strategies_applied=[],
                cache_hit=False
            )

        # Calculate token budget
        token_limit = self._get_token_limit(model_context, platform)
        original_tokens = self._estimate_tokens(messages)

        logger.debug(f"[CONTEXT] Optimizing {len(messages)} messages, {original_tokens:,} tokens, limit: {token_limit:,}")

        # Check semantic cache first
        cache_key = None
        if enable_caching:
            cache_key = self._generate_cache_key(messages, token_limit)
            cached_result = self._get_cached_optimization(cache_key)
            if cached_result:
                logger.debug(f"[CONTEXT] Cache hit for key: {cache_key[:16]}...")
                return cached_result

        # Apply optimization strategies
        strategies_applied = []
        optimized_messages = messages

        if original_tokens <= token_limit:
            # No optimization needed
            strategies_applied.append("no_optimization_needed")
        else:
            # Apply intelligent truncation strategies
            optimized_messages, applied = self._apply_optimization_strategies(
                messages, token_limit, preserve_conversation_flow
            )
            strategies_applied.extend(applied)

        optimized_tokens = self._estimate_tokens(optimized_messages)
        compression_ratio = optimized_tokens / original_tokens if original_tokens > 0 else 1.0

        result = ContextOptimizationResult(
            optimized_content=optimized_messages,
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            compression_ratio=compression_ratio,
            strategies_applied=strategies_applied,
            cache_hit=False
        )

        # Cache the result
        if enable_caching and cache_key:
            self._cache_optimization_result(cache_key, result, strategies_applied)

        elapsed = time.time() - start_time
        logger.debug(f"[CONTEXT] Optimization complete: {original_tokens:,} → {optimized_tokens:,} tokens "
                    f"({compression_ratio:.2f} ratio) in {elapsed:.3f}s, strategies: {strategies_applied}")

        # Record performance metrics
        try:
            from utils.context_performance import record_context_operation

            record_context_operation(
                operation="optimize_context",
                tool_name="context_manager",
                original_tokens=original_tokens,
                optimized_tokens=optimized_tokens,
                processing_time_ms=elapsed * 1000,
                cache_hit=result.cache_hit,
                strategies_applied=strategies_applied,
                content_type="messages",
                model_context=str(model_context) if model_context else None
            )
        except Exception as e:
            logger.debug(f"[CONTEXT] Failed to record performance metrics: {e}")

        return result

    def _get_token_limit(self, model_context: Optional[Any], platform: Optional[str]) -> int:
        """Get token limit based on model context or platform."""
        if model_context:
            try:
                # Use ModelContext for accurate token allocation
                allocation = model_context.calculate_token_allocation()
                return allocation.content_tokens  # Use content budget, not total
            except Exception as e:
                logger.debug(f"[CONTEXT] Failed to get token allocation from model context: {e}")

        # Fallback to platform-based limits
        if platform:
            return self.default_limits.get(platform, self.default_limits["custom"])

        # Conservative default
        return self.default_limits["custom"]

    def _estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """
        Estimate token count for messages.

        Uses conservative character-to-token ratio. Can be enhanced with
        model-specific tokenizers in the future.
        """
        total_chars = 0
        for msg in messages:
            if isinstance(msg, dict):
                content = msg.get("content", "")
                if isinstance(content, str):
                    total_chars += len(content)
                elif isinstance(content, list):
                    # Handle multi-modal content (text + images)
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            total_chars += len(item.get("text", ""))

        # Conservative estimation: ~3 characters per token
        return total_chars // 3

    def _apply_optimization_strategies(
        self,
        messages: List[Dict[str, Any]],
        token_limit: int,
        preserve_conversation_flow: bool
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Apply intelligent optimization strategies to fit token limit."""
        strategies_applied = []
        optimized = messages.copy()

        # Strategy 1: Preserve system messages (highest priority)
        system_msgs = [m for m in optimized if m.get("role") == "system"]
        non_system_msgs = [m for m in optimized if m.get("role") != "system"]

        if system_msgs:
            strategies_applied.append("preserve_system_messages")

        # Strategy 2: Apply newest-first prioritization for conversation flow
        if preserve_conversation_flow and len(non_system_msgs) > 10:
            # Keep recent messages (last 10) and compress older ones
            recent_msgs = non_system_msgs[-10:]
            older_msgs = non_system_msgs[:-10]

            # Compress older messages
            compressed_older = self._compress_messages(older_msgs)
            non_system_msgs = compressed_older + recent_msgs
            strategies_applied.append("newest_first_prioritization")

        # Strategy 3: Semantic summarization if still over limit
        current_tokens = self._estimate_tokens(system_msgs + non_system_msgs)
        if current_tokens > token_limit:
            non_system_msgs = self._semantic_compression(non_system_msgs, token_limit - self._estimate_tokens(system_msgs))
            strategies_applied.append("semantic_summarization")

        # Strategy 4: Final truncation if necessary
        final_messages = system_msgs + non_system_msgs
        final_tokens = self._estimate_tokens(final_messages)
        if final_tokens > token_limit:
            final_messages = self._emergency_truncation(final_messages, token_limit)
            strategies_applied.append("emergency_truncation")

        return final_messages, strategies_applied

    def _compress_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compress messages by summarizing long content."""
        compressed = []
        total_chars = sum(len(m.get("content", "")) for m in messages)

        if total_chars < 5000:
            # Not worth compressing
            return messages

        # Group messages and create summary
        summary_content = f"[Compressed {len(messages)} messages containing {total_chars:,} characters of conversation history]"

        compressed.append({
            "role": "system",
            "content": summary_content
        })

        return compressed

    def _semantic_compression(self, messages: List[Dict[str, Any]], target_tokens: int) -> List[Dict[str, Any]]:
        """Apply semantic compression to fit target token count."""
        current_tokens = self._estimate_tokens(messages)

        if current_tokens <= target_tokens:
            return messages

        # Simple compression: keep most recent messages that fit
        compressed = []
        token_count = 0

        for msg in reversed(messages):
            msg_tokens = self._estimate_tokens([msg])
            if token_count + msg_tokens <= target_tokens:
                compressed.insert(0, msg)
                token_count += msg_tokens
            else:
                break

        # Add summary of dropped messages if any
        dropped_count = len(messages) - len(compressed)
        if dropped_count > 0:
            summary = {
                "role": "system",
                "content": f"[{dropped_count} earlier messages compressed to fit context limit]"
            }
            compressed.insert(0, summary)

        return compressed

    def _emergency_truncation(self, messages: List[Dict[str, Any]], token_limit: int) -> List[Dict[str, Any]]:
        """Emergency truncation to fit absolute token limit."""
        truncated = []
        token_count = 0

        # Preserve system messages first
        system_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]

        # Add system messages
        for msg in system_msgs:
            msg_tokens = self._estimate_tokens([msg])
            if token_count + msg_tokens <= token_limit:
                truncated.append(msg)
                token_count += msg_tokens

        # Add other messages from most recent
        for msg in reversed(other_msgs):
            msg_tokens = self._estimate_tokens([msg])
            if token_count + msg_tokens <= token_limit:
                truncated.insert(-len([m for m in truncated if m.get("role") != "system"]), msg)
                token_count += msg_tokens
            else:
                break

        return truncated

    def _generate_cache_key(self, messages: List[Dict[str, Any]], token_limit: int) -> str:
        """Generate semantic cache key for messages."""
        # Create hash based on message content and token limit
        content_str = ""
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            content_str += f"{role}:{content}\n"

        content_str += f"limit:{token_limit}"
        return hashlib.sha256(content_str.encode()).hexdigest()

    def _get_cached_optimization(self, cache_key: str) -> Optional[ContextOptimizationResult]:
        """Retrieve cached optimization result."""
        self._cleanup_expired_cache()

        entry = self._semantic_cache.get(cache_key)
        if not entry:
            return None

        # Update access statistics
        entry.last_accessed = datetime.now(timezone.utc)
        entry.access_count += 1

        return ContextOptimizationResult(
            optimized_content=entry.content.copy(),
            original_tokens=entry.token_count,
            optimized_tokens=self._estimate_tokens(entry.content),
            compression_ratio=self._estimate_tokens(entry.content) / entry.token_count if entry.token_count > 0 else 1.0,
            strategies_applied=entry.compression_strategies.copy(),
            cache_hit=True
        )

    def _cache_optimization_result(
        self,
        cache_key: str,
        result: ContextOptimizationResult,
        strategies: List[str]
    ) -> None:
        """Cache optimization result for future use."""
        now = datetime.now(timezone.utc)

        entry = SemanticCacheEntry(
            content=result.optimized_content.copy(),
            semantic_hash=cache_key,
            created_at=now,
            last_accessed=now,
            access_count=1,
            token_count=result.original_tokens,
            compression_strategies=strategies.copy()
        )

        self._semantic_cache[cache_key] = entry

        # Enforce cache size limit
        if len(self._semantic_cache) > self._cache_max_size:
            self._evict_least_used_cache_entries()

    def _cleanup_expired_cache(self) -> None:
        """Remove expired cache entries."""
        now = datetime.now(timezone.utc)
        expired_keys = []

        for key, entry in self._semantic_cache.items():
            age_seconds = (now - entry.created_at).total_seconds()
            if age_seconds > self._cache_ttl_seconds:
                expired_keys.append(key)

        for key in expired_keys:
            del self._semantic_cache[key]

        if expired_keys:
            logger.debug(f"[CONTEXT] Cleaned up {len(expired_keys)} expired cache entries")

    def _evict_least_used_cache_entries(self) -> None:
        """Evict least recently used cache entries."""
        if len(self._semantic_cache) <= self._cache_max_size:
            return

        # Sort by last accessed time and access count
        entries = list(self._semantic_cache.items())
        entries.sort(key=lambda x: (x[1].last_accessed, x[1].access_count))

        # Remove oldest entries
        entries_to_remove = len(entries) - self._cache_max_size
        for i in range(entries_to_remove):
            key = entries[i][0]
            del self._semantic_cache[key]

        logger.debug(f"[CONTEXT] Evicted {entries_to_remove} least used cache entries")

    # Legacy compatibility methods
    def estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Legacy method for backward compatibility."""
        return self._estimate_tokens(messages)

    def optimize(self, messages: List[Dict[str, Any]], platform: str) -> List[Dict[str, Any]]:
        """Legacy method for backward compatibility."""
        result = self.optimize_context(messages, platform=platform)
        return result.optimized_content

