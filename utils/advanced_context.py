"""
Advanced Context Utilities

Provides easy-to-use functions for integrating the Advanced Context Manager
with existing tools and workflows. This module serves as a bridge between
the new context management system and legacy code.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


def optimize_for_model(
    content: Union[str, List[Dict[str, Any]]],
    model_context: Optional[Any] = None,
    preserve_conversation_flow: bool = True,
    enable_caching: bool = True
) -> Tuple[Union[str, List[Dict[str, Any]]], Dict[str, Any]]:
    """
    Optimize content for a specific model's token limits.
    
    This is the main entry point for tools that want to optimize content
    without dealing with the complexity of the Advanced Context Manager directly.
    
    Args:
        content: Content to optimize (string or list of messages)
        model_context: ModelContext instance for token budget calculation
        preserve_conversation_flow: Whether to maintain conversation chronology
        enable_caching: Whether to use semantic caching
        
    Returns:
        Tuple of (optimized_content, optimization_metadata)
        
    Example:
        from utils.advanced_context import optimize_for_model
        
        # In a tool's execute method:
        optimized_prompt, metadata = optimize_for_model(
            content=long_prompt,
            model_context=self._model_context
        )
    """
    try:
        from src.core.agentic.context_integration import get_context_integration_manager
        
        integration_manager = get_context_integration_manager()
        
        # Use the context manager directly for simple optimization
        result = integration_manager.context_manager.optimize_context(
            content=content,
            model_context=model_context,
            preserve_conversation_flow=preserve_conversation_flow,
            enable_caching=enable_caching
        )
        
        metadata = {
            "original_tokens": result.original_tokens,
            "optimized_tokens": result.optimized_tokens,
            "compression_ratio": result.compression_ratio,
            "strategies_applied": result.strategies_applied,
            "cache_hit": result.cache_hit,
            "token_savings": result.original_tokens - result.optimized_tokens
        }
        
        return result.optimized_content, metadata
        
    except Exception as e:
        logger.error(f"[ADVANCED_CONTEXT] Failed to optimize content: {e}")
        # Fallback to original content
        return content, {"error": str(e), "fallback": True}


def optimize_conversation_thread(
    thread_context: Any,
    model_context: Any,
    include_files: bool = True
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Optimize conversation thread context for token limits.
    
    Integrates with the conversation memory system to provide optimized
    conversation history that respects model token budgets.
    
    Args:
        thread_context: ThreadContext from utils.conversation_memory
        model_context: ModelContext for token allocation
        include_files: Whether to include file references in optimization
        
    Returns:
        Tuple of (optimized_messages, optimization_metadata)
        
    Example:
        from utils.advanced_context import optimize_conversation_thread
        
        # In a tool that uses conversation memory:
        thread = get_thread(continuation_id)
        optimized_history, metadata = optimize_conversation_thread(
            thread_context=thread,
            model_context=self._model_context
        )
    """
    try:
        from src.core.agentic.context_integration import get_context_integration_manager
        
        integration_manager = get_context_integration_manager()
        
        return integration_manager.optimize_conversation_context(
            thread_context=thread_context,
            model_context=model_context,
            include_files=include_files,
            preserve_flow=True
        )
        
    except Exception as e:
        logger.error(f"[ADVANCED_CONTEXT] Failed to optimize conversation thread: {e}")
        # Fallback to empty conversation
        return [], {"error": str(e), "fallback": True}


def optimize_file_content(
    file_content: str,
    file_paths: List[str],
    model_context: Any,
    context_label: str = "Context files"
) -> Tuple[str, Dict[str, Any]]:
    """
    Optimize file content for inclusion in prompts.
    
    Integrates with file processing to provide optimized file content
    that respects model token budgets while preserving essential information.
    
    Args:
        file_content: Formatted file content string
        file_paths: List of file paths being included
        model_context: ModelContext for token allocation
        context_label: Label for the file context section
        
    Returns:
        Tuple of (optimized_content, optimization_metadata)
        
    Example:
        from utils.advanced_context import optimize_file_content
        
        # In a tool that processes files:
        file_content, _ = self._prepare_file_content_for_prompt(files)
        optimized_content, metadata = optimize_file_content(
            file_content=file_content,
            file_paths=files,
            model_context=self._model_context
        )
    """
    try:
        from src.core.agentic.context_integration import get_context_integration_manager
        
        integration_manager = get_context_integration_manager()
        
        return integration_manager.optimize_file_context(
            file_content=file_content,
            file_paths=file_paths,
            model_context=model_context,
            context_label=context_label
        )
        
    except Exception as e:
        logger.error(f"[ADVANCED_CONTEXT] Failed to optimize file content: {e}")
        # Fallback to original content
        return file_content, {"error": str(e), "fallback": True}


def optimize_cross_tool_context(
    current_tool: str,
    previous_tool: str,
    thread_context: Any,
    model_context: Any,
    preserve_tool_transitions: bool = True
) -> Tuple[str, Dict[str, Any]]:
    """
    Optimize context for cross-tool continuity.

    Provides enhanced context optimization when switching between tools
    in a conversation thread, ensuring important context is preserved
    across tool boundaries.

    Args:
        current_tool: Name of the current tool being executed
        previous_tool: Name of the previous tool in the conversation
        thread_context: ThreadContext from conversation memory
        model_context: ModelContext for token allocation
        preserve_tool_transitions: Whether to preserve tool transition markers

    Returns:
        Tuple of (optimized_context, optimization_metadata)

    Example:
        from utils.advanced_context import optimize_cross_tool_context

        # In a tool that continues from another tool:
        thread = get_thread(continuation_id)
        optimized_context, metadata = optimize_cross_tool_context(
            current_tool="codereview",
            previous_tool="analyze",
            thread_context=thread,
            model_context=self._model_context
        )
    """
    try:
        from src.core.agentic.context_integration import get_context_integration_manager

        integration_manager = get_context_integration_manager()

        return integration_manager.optimize_cross_tool_context(
            current_tool=current_tool,
            previous_tool=previous_tool,
            thread_context=thread_context,
            model_context=model_context,
            preserve_tool_transitions=preserve_tool_transitions
        )

    except Exception as e:
        logger.error(f"[ADVANCED_CONTEXT] Failed to optimize cross-tool context: {e}")
        # Fallback to empty context
        return "", {"error": str(e)}


def estimate_tokens(content: Union[str, List[Dict[str, Any]]]) -> int:
    """
    Estimate token count for content using the Advanced Context Manager.

    Provides a more accurate token estimation than simple character counting.

    Args:
        content: Content to estimate (string or list of messages)

    Returns:
        Estimated token count

    Example:
        from utils.advanced_context import estimate_tokens

        token_count = estimate_tokens(prompt_text)
        if token_count > model_limit:
            # Apply optimization
    """
    try:
        # Handle None input
        if content is None:
            return 0

        from src.core.agentic.context_manager import AdvancedContextManager

        context_manager = AdvancedContextManager()

        if isinstance(content, str):
            messages = [{"role": "user", "content": content}]
        else:
            messages = content if content else []

        return context_manager._estimate_tokens(messages)

    except Exception as e:
        logger.error(f"[ADVANCED_CONTEXT] Failed to estimate tokens: {e}")
        # Fallback to simple character-based estimation
        if content is None:
            return 0
        elif isinstance(content, str):
            return len(content) // 3
        elif isinstance(content, list):
            total_chars = sum(len(str(msg.get("content", ""))) for msg in content if isinstance(msg, dict))
            return total_chars // 3
        else:
            return 0


def get_context_stats() -> Dict[str, Any]:
    """
    Get comprehensive statistics about context optimization usage.

    Returns:
        Dictionary with optimization statistics including performance metrics

    Example:
        from utils.advanced_context import get_context_stats

        stats = get_context_stats()
        logger.info(f"Context cache hit rate: {stats.get('cache_hit_rate', 0):.2%}")
        logger.info(f"Average optimization time: {stats.get('avg_optimization_time_ms', 0):.1f}ms")
    """
    try:
        from src.core.agentic.context_integration import get_context_integration_manager
        from utils.context_performance import get_context_performance_summary

        # Get basic context manager stats
        integration_manager = get_context_integration_manager()
        basic_stats = integration_manager.get_optimization_stats()

        # Get comprehensive performance stats
        performance_stats = get_context_performance_summary(last_n_minutes=60)  # Last hour

        # Combine stats
        combined_stats = {
            **basic_stats,
            "performance": performance_stats,
            "timestamp": time.time()
        }

        return combined_stats

    except Exception as e:
        logger.error(f"[ADVANCED_CONTEXT] Failed to get context stats: {e}")
        return {"error": str(e)}


def get_context_performance_recommendations() -> List[str]:
    """
    Get performance optimization recommendations for context management.

    Returns:
        List of actionable optimization recommendations

    Example:
        from utils.advanced_context import get_context_performance_recommendations

        recommendations = get_context_performance_recommendations()
        for rec in recommendations:
            logger.info(f"Optimization recommendation: {rec}")
    """
    try:
        from utils.context_performance import get_context_optimization_recommendations

        return get_context_optimization_recommendations()

    except Exception as e:
        logger.error(f"[ADVANCED_CONTEXT] Failed to get performance recommendations: {e}")
        return [f"Error getting recommendations: {e}"]


def clear_context_cache() -> bool:
    """
    Clear the semantic context cache.
    
    Useful for testing or when memory usage needs to be reduced.
    
    Returns:
        True if cache was cleared successfully, False otherwise
        
    Example:
        from utils.advanced_context import clear_context_cache
        
        if clear_context_cache():
            logger.info("Context cache cleared")
    """
    try:
        from src.core.agentic.context_integration import get_context_integration_manager
        
        integration_manager = get_context_integration_manager()
        integration_manager.context_manager._semantic_cache.clear()
        
        logger.info("[ADVANCED_CONTEXT] Context cache cleared")
        return True
        
    except Exception as e:
        logger.error(f"[ADVANCED_CONTEXT] Failed to clear context cache: {e}")
        return False


# Backward compatibility aliases for existing code
def optimize_context(content, model_context=None, **kwargs):
    """Backward compatibility alias for optimize_for_model."""
    return optimize_for_model(content, model_context, **kwargs)


def smart_truncate(content, token_limit, **kwargs):
    """
    Smart truncation with token limit.
    
    Backward compatibility function that provides intelligent truncation
    based on token limits rather than character counts.
    """
    try:
        from src.core.agentic.context_manager import AdvancedContextManager
        
        context_manager = AdvancedContextManager()
        
        # Create a mock model context with the specified limit
        class MockModelContext:
            def calculate_token_allocation(self):
                class MockAllocation:
                    content_tokens = token_limit
                return MockAllocation()
        
        mock_context = MockModelContext()
        
        result = context_manager.optimize_context(
            content=content,
            model_context=mock_context,
            **kwargs
        )
        
        return result.optimized_content
        
    except Exception as e:
        logger.error(f"[ADVANCED_CONTEXT] Smart truncate failed: {e}")
        # Fallback to simple truncation
        if isinstance(content, str):
            # Simple character-based truncation
            max_chars = token_limit * 3  # Rough conversion
            return content[:max_chars] if len(content) > max_chars else content
        else:
            return content
