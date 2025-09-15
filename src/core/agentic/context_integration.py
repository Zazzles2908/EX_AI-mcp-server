"""
Context Manager Integration Module

This module provides seamless integration between the Advanced Context Manager
and existing systems like conversation memory, model context, and file processing.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .context_manager import AdvancedContextManager, ContextOptimizationResult

logger = logging.getLogger(__name__)


class ContextIntegrationManager:
    """
    Integration layer between Advanced Context Manager and existing systems.
    
    Provides unified interface for context optimization across:
    - utils.conversation_memory (thread context reconstruction)
    - utils.model_context (token allocation)
    - tools.shared.base_tool (file processing)
    - tools.workflow.workflow_mixin (workflow context)
    """
    
    def __init__(self):
        self.context_manager = AdvancedContextManager()
        self._integration_cache = {}
        self._cross_tool_context_cache = {}  # Cache for cross-tool context optimization
    
    def optimize_conversation_context(
        self,
        thread_context: Any,
        model_context: Any,
        include_files: bool = True,
        preserve_flow: bool = True
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Optimize conversation context from thread reconstruction.
        
        Integrates with utils.conversation_memory.ThreadContext to provide
        optimized conversation history that respects token budgets.
        
        Args:
            thread_context: ThreadContext from conversation memory
            model_context: ModelContext for token allocation
            include_files: Whether to include file references
            preserve_flow: Whether to preserve conversation chronology
            
        Returns:
            Tuple of (optimized_messages, metadata)
        """
        try:
            # Extract conversation turns from thread context
            messages = []
            
            if hasattr(thread_context, 'turns'):
                for turn in thread_context.turns:
                    if hasattr(turn, 'role') and hasattr(turn, 'content'):
                        message = {
                            "role": turn.role,
                            "content": turn.content
                        }
                        
                        # Add file references if requested
                        if include_files and hasattr(turn, 'files') and turn.files:
                            file_refs = [f"File: {f}" for f in turn.files]
                            message["content"] += f"\n\nReferenced files:\n" + "\n".join(file_refs)
                        
                        messages.append(message)
            
            # Optimize using Advanced Context Manager
            result = self.context_manager.optimize_context(
                content=messages,
                model_context=model_context,
                preserve_conversation_flow=preserve_flow,
                enable_caching=True
            )
            
            metadata = {
                "original_turns": len(messages),
                "optimized_turns": len(result.optimized_content),
                "original_tokens": result.original_tokens,
                "optimized_tokens": result.optimized_tokens,
                "compression_ratio": result.compression_ratio,
                "strategies_applied": result.strategies_applied,
                "cache_hit": result.cache_hit,
                "thread_id": getattr(thread_context, 'thread_id', None)
            }
            
            logger.debug(f"[CONTEXT_INTEGRATION] Optimized conversation: "
                        f"{metadata['original_turns']} → {metadata['optimized_turns']} turns, "
                        f"{metadata['original_tokens']:,} → {metadata['optimized_tokens']:,} tokens")

            # Record performance metrics
            try:
                from utils.context_performance import record_context_operation

                record_context_operation(
                    operation="optimize_conversation_thread",
                    tool_name="context_integration",
                    original_tokens=metadata['original_tokens'],
                    optimized_tokens=metadata['optimized_tokens'],
                    processing_time_ms=0,  # Time tracked in context_manager
                    cache_hit=metadata['cache_hit'],
                    strategies_applied=metadata['strategies_applied'],
                    content_type="conversation",
                    model_context=str(model_context) if model_context else None
                )
            except Exception as e:
                logger.debug(f"[CONTEXT_INTEGRATION] Failed to record conversation performance metrics: {e}")

            return result.optimized_content, metadata
            
        except Exception as e:
            logger.error(f"[CONTEXT_INTEGRATION] Failed to optimize conversation context: {e}")
            # Fallback to original messages
            return [], {"error": str(e)}
    
    def optimize_file_context(
        self,
        file_content: str,
        file_paths: List[str],
        model_context: Any,
        context_label: str = "Context files"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Optimize file context for inclusion in prompts.
        
        Integrates with file processing from tools.shared.base_tool to provide
        optimized file content that respects token budgets.
        
        Args:
            file_content: Formatted file content string
            file_paths: List of file paths being included
            model_context: ModelContext for token allocation
            context_label: Label for the file context section
            
        Returns:
            Tuple of (optimized_content, metadata)
        """
        try:
            # Convert file content to message format for optimization
            file_message = {
                "role": "system",
                "content": f"=== {context_label.upper()} ===\n{file_content}\n=== END {context_label.upper()} ==="
            }
            
            # Optimize using Advanced Context Manager
            result = self.context_manager.optimize_context(
                content=[file_message],
                model_context=model_context,
                preserve_conversation_flow=False,  # Files don't need conversation flow
                enable_caching=True
            )
            
            # Extract optimized content
            optimized_content = ""
            if result.optimized_content:
                optimized_content = result.optimized_content[0].get("content", "")
            
            metadata = {
                "file_count": len(file_paths),
                "original_tokens": result.original_tokens,
                "optimized_tokens": result.optimized_tokens,
                "compression_ratio": result.compression_ratio,
                "strategies_applied": result.strategies_applied,
                "cache_hit": result.cache_hit,
                "file_paths": file_paths
            }
            
            logger.debug(f"[CONTEXT_INTEGRATION] Optimized file context: "
                        f"{len(file_paths)} files, "
                        f"{metadata['original_tokens']:,} → {metadata['optimized_tokens']:,} tokens")

            # Record performance metrics
            try:
                from utils.context_performance import record_context_operation

                record_context_operation(
                    operation="optimize_file_content",
                    tool_name="context_integration",
                    original_tokens=metadata['original_tokens'],
                    optimized_tokens=metadata['optimized_tokens'],
                    processing_time_ms=0,  # Time tracked in context_manager
                    cache_hit=metadata['cache_hit'],
                    strategies_applied=metadata['strategies_applied'],
                    content_type="file",
                    model_context=str(model_context) if model_context else None
                )
            except Exception as e:
                logger.debug(f"[CONTEXT_INTEGRATION] Failed to record file performance metrics: {e}")

            return optimized_content, metadata
            
        except Exception as e:
            logger.error(f"[CONTEXT_INTEGRATION] Failed to optimize file context: {e}")
            # Fallback to original content
            return file_content, {"error": str(e)}

    def optimize_cross_tool_context(
        self,
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
            Tuple of (optimized_context, metadata)
        """
        try:
            # Create cache key for cross-tool optimization
            cache_key = f"{previous_tool}->{current_tool}:{getattr(thread_context, 'thread_id', 'unknown')}"

            # Check cache first
            if cache_key in self._cross_tool_context_cache:
                cached_result = self._cross_tool_context_cache[cache_key]
                logger.debug(f"[CONTEXT_INTEGRATION] Cross-tool context cache hit: {cache_key}")
                return cached_result

            # Extract conversation context with tool transition awareness
            messages = []

            if hasattr(thread_context, 'turns'):
                for turn in thread_context.turns:
                    if hasattr(turn, 'role') and hasattr(turn, 'content'):
                        message = {
                            "role": turn.role,
                            "content": turn.content
                        }

                        # Add tool transition markers if requested
                        if preserve_tool_transitions and hasattr(turn, 'tool_name') and turn.tool_name:
                            if turn.tool_name != current_tool:
                                message["content"] = f"[Tool: {turn.tool_name}] {message['content']}"

                        # Add file references for cross-tool context
                        if hasattr(turn, 'files') and turn.files:
                            file_refs = [f"File: {f}" for f in turn.files]
                            message["content"] += f"\n\nReferenced files:\n" + "\n".join(file_refs)

                        messages.append(message)

            # Apply cross-tool specific optimization strategies
            result = self.context_manager.optimize_context(
                content=messages,
                model_context=model_context,
                preserve_conversation_flow=True,
                enable_caching=True
            )

            # Build optimized context string
            optimized_context = ""
            if result.optimized_content:
                context_parts = [
                    f"=== CROSS-TOOL CONTEXT ({previous_tool} → {current_tool}) ===",
                    f"Thread: {getattr(thread_context, 'thread_id', 'unknown')}",
                    f"Previous tool: {previous_tool}",
                    f"Current tool: {current_tool}",
                    "",
                ]

                for i, message in enumerate(result.optimized_content):
                    role_label = "Claude" if message.get("role") == "user" else "Assistant"
                    context_parts.append(f"\n--- Turn {i+1} ({role_label}) ---")
                    context_parts.append(message.get("content", ""))

                context_parts.append("\n=== END CROSS-TOOL CONTEXT ===")
                optimized_context = "\n".join(context_parts)

            # Prepare metadata
            metadata = {
                "optimized": result.compression_ratio < 1.0,
                "compression_ratio": result.compression_ratio,
                "strategies_applied": result.strategies_applied,
                "original_tokens": result.original_tokens,
                "optimized_tokens": result.optimized_tokens,
                "cache_hit": result.cache_hit,
                "cross_tool_transition": f"{previous_tool} → {current_tool}"
            }

            # Cache the result for future use
            cache_result = (optimized_context, metadata)
            self._cross_tool_context_cache[cache_key] = cache_result

            logger.debug(
                f"[CONTEXT_INTEGRATION] Cross-tool context optimized: {previous_tool} → {current_tool} "
                f"({result.compression_ratio:.2f} ratio, {len(result.strategies_applied)} strategies)"
            )

            # Record performance metrics
            try:
                from utils.context_performance import record_context_operation

                record_context_operation(
                    operation="optimize_cross_tool_context",
                    tool_name=current_tool,
                    original_tokens=metadata['original_tokens'],
                    optimized_tokens=metadata['optimized_tokens'],
                    processing_time_ms=0,  # Time tracked in context_manager
                    cache_hit=metadata['cache_hit'],
                    strategies_applied=metadata['strategies_applied'],
                    content_type="cross_tool",
                    model_context=str(model_context) if model_context else None
                )
            except Exception as e:
                logger.debug(f"[CONTEXT_INTEGRATION] Failed to record cross-tool performance metrics: {e}")

            return cache_result

        except Exception as e:
            logger.error(f"[CONTEXT_INTEGRATION] Failed to optimize cross-tool context: {e}")
            # Fallback to basic context
            return "", {"error": str(e)}
    
    def optimize_workflow_context(
        self,
        workflow_data: Dict[str, Any],
        model_context: Any,
        step_number: int,
        is_final_step: bool
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Optimize workflow context for multi-step processes.
        
        Integrates with tools.workflow.workflow_mixin to provide optimized
        context for workflow steps that respects token budgets and step requirements.
        
        Args:
            workflow_data: Workflow step data
            model_context: ModelContext for token allocation
            step_number: Current step number
            is_final_step: Whether this is the final step
            
        Returns:
            Tuple of (optimized_workflow_data, metadata)
        """
        try:
            # Extract relevant content for optimization
            content_parts = []
            
            # Add step context
            if "step" in workflow_data:
                content_parts.append({
                    "role": "system",
                    "content": f"Step {step_number}: {workflow_data['step']}"
                })
            
            # Add findings
            if "findings" in workflow_data:
                content_parts.append({
                    "role": "assistant", 
                    "content": f"Findings: {workflow_data['findings']}"
                })
            
            # Add relevant files context
            if "relevant_files" in workflow_data and workflow_data["relevant_files"]:
                file_list = "\n".join(workflow_data["relevant_files"])
                content_parts.append({
                    "role": "system",
                    "content": f"Relevant files:\n{file_list}"
                })
            
            # Optimize based on step type
            preserve_flow = not is_final_step  # Final steps need full context
            
            result = self.context_manager.optimize_context(
                content=content_parts,
                model_context=model_context,
                preserve_conversation_flow=preserve_flow,
                enable_caching=True
            )
            
            # Reconstruct optimized workflow data
            optimized_data = workflow_data.copy()
            
            # Update with optimized content if compression occurred
            if result.compression_ratio < 0.9:  # Significant compression
                optimized_content = "\n".join([msg.get("content", "") for msg in result.optimized_content])
                optimized_data["_optimized_context"] = optimized_content
                optimized_data["_context_metadata"] = {
                    "compression_ratio": result.compression_ratio,
                    "strategies_applied": result.strategies_applied
                }
            
            metadata = {
                "step_number": step_number,
                "is_final_step": is_final_step,
                "original_tokens": result.original_tokens,
                "optimized_tokens": result.optimized_tokens,
                "compression_ratio": result.compression_ratio,
                "strategies_applied": result.strategies_applied,
                "cache_hit": result.cache_hit
            }
            
            logger.debug(f"[CONTEXT_INTEGRATION] Optimized workflow step {step_number}: "
                        f"{metadata['original_tokens']:,} → {metadata['optimized_tokens']:,} tokens")
            
            return optimized_data, metadata
            
        except Exception as e:
            logger.error(f"[CONTEXT_INTEGRATION] Failed to optimize workflow context: {e}")
            # Fallback to original data
            return workflow_data, {"error": str(e)}
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics from the context manager."""
        cache_stats = {
            "cache_size": len(self.context_manager._semantic_cache),
            "cache_max_size": self.context_manager._cache_max_size,
            "cache_ttl_seconds": self.context_manager._cache_ttl_seconds
        }
        
        # Calculate cache hit rate
        total_entries = len(self.context_manager._semantic_cache)
        if total_entries > 0:
            total_accesses = sum(entry.access_count for entry in self.context_manager._semantic_cache.values())
            cache_stats["total_accesses"] = total_accesses
            cache_stats["average_accesses_per_entry"] = total_accesses / total_entries
        
        return cache_stats


# Global instance for easy access
_context_integration_manager = None

def get_context_integration_manager() -> ContextIntegrationManager:
    """Get the global context integration manager instance."""
    global _context_integration_manager
    if _context_integration_manager is None:
        _context_integration_manager = ContextIntegrationManager()
    return _context_integration_manager
