"""
Comprehensive performance monitoring and optimization for context management operations.

Provides detailed metrics, performance tracking, and optimization recommendations
for Advanced Context Manager operations across the EX MCP Server.
"""
from __future__ import annotations

import json
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class ContextPerformanceMetric:
    """Individual context performance measurement."""
    timestamp: float
    operation: str  # 'optimize_file_content', 'optimize_conversation', 'cross_tool_context', etc.
    tool_name: str
    original_tokens: int
    optimized_tokens: int
    compression_ratio: float
    processing_time_ms: float
    cache_hit: bool
    strategies_applied: List[str]
    content_type: str  # 'file', 'conversation', 'cross_tool', etc.
    model_context: Optional[str] = None
    error: Optional[str] = None


class ContextPerformanceMonitor:
    """
    Comprehensive performance monitoring for context management operations.
    
    Tracks metrics, identifies performance bottlenecks, and provides optimization
    recommendations for Advanced Context Manager usage.
    """
    
    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self._metrics: deque[ContextPerformanceMetric] = deque(maxlen=max_metrics)
        self._lock = threading.Lock()
        
        # Performance aggregations
        self._operation_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "count": 0,
            "total_time_ms": 0.0,
            "total_original_tokens": 0,
            "total_optimized_tokens": 0,
            "cache_hits": 0,
            "errors": 0,
            "strategies_used": defaultdict(int)
        })
        
        # Tool-specific performance tracking
        self._tool_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "operations": 0,
            "total_time_ms": 0.0,
            "avg_compression_ratio": 0.0,
            "cache_hit_rate": 0.0,
            "most_common_strategies": []
        })
    
    def record_operation(
        self,
        operation: str,
        tool_name: str,
        original_tokens: int,
        optimized_tokens: int,
        processing_time_ms: float,
        cache_hit: bool = False,
        strategies_applied: Optional[List[str]] = None,
        content_type: str = "unknown",
        model_context: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """Record a context management operation for performance tracking."""
        strategies_applied = strategies_applied or []
        compression_ratio = optimized_tokens / original_tokens if original_tokens > 0 else 1.0
        
        metric = ContextPerformanceMetric(
            timestamp=time.time(),
            operation=operation,
            tool_name=tool_name,
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            compression_ratio=compression_ratio,
            processing_time_ms=processing_time_ms,
            cache_hit=cache_hit,
            strategies_applied=strategies_applied,
            content_type=content_type,
            model_context=model_context,
            error=error
        )
        
        with self._lock:
            self._metrics.append(metric)
            self._update_aggregations(metric)
        
        # Log performance data for observability
        self._log_performance_data(metric)
    
    def _update_aggregations(self, metric: ContextPerformanceMetric) -> None:
        """Update performance aggregations with new metric."""
        # Update operation stats
        op_stats = self._operation_stats[metric.operation]
        op_stats["count"] += 1
        op_stats["total_time_ms"] += metric.processing_time_ms
        op_stats["total_original_tokens"] += metric.original_tokens
        op_stats["total_optimized_tokens"] += metric.optimized_tokens
        
        if metric.cache_hit:
            op_stats["cache_hits"] += 1
        if metric.error:
            op_stats["errors"] += 1
        
        for strategy in metric.strategies_applied:
            op_stats["strategies_used"][strategy] += 1
        
        # Update tool stats
        tool_stats = self._tool_stats[metric.tool_name]
        tool_stats["operations"] += 1
        tool_stats["total_time_ms"] += metric.processing_time_ms
        
        # Update running averages
        if tool_stats["operations"] > 0:
            tool_stats["avg_compression_ratio"] = (
                (tool_stats["avg_compression_ratio"] * (tool_stats["operations"] - 1) + metric.compression_ratio) 
                / tool_stats["operations"]
            )
    
    def _log_performance_data(self, metric: ContextPerformanceMetric) -> None:
        """Log performance data for external monitoring."""
        try:
            from utils.observability import record_token_usage
            
            # Record token usage for observability
            record_token_usage(
                model=metric.model_context or "unknown",
                input_tokens=metric.original_tokens,
                output_tokens=metric.optimized_tokens,
                tool_name=metric.tool_name
            )
            
            # Log detailed performance data
            perf_data = {
                "timestamp": metric.timestamp,
                "event_type": "context_performance",
                "operation": metric.operation,
                "tool": metric.tool_name,
                "processing_time_ms": metric.processing_time_ms,
                "compression_ratio": metric.compression_ratio,
                "cache_hit": metric.cache_hit,
                "content_type": metric.content_type,
                "strategies_count": len(metric.strategies_applied),
                "error": metric.error is not None
            }
            
            # Write to metrics log if available
            try:
                import os
                metrics_path = os.getenv("EX_METRICS_LOG_PATH", ".logs/metrics.jsonl")
                if metrics_path:
                    with open(metrics_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(perf_data) + "\n")
            except Exception:
                pass  # Best effort logging
                
        except Exception as e:
            logger.debug(f"Failed to log performance data: {e}")
    
    def get_performance_summary(self, last_n_minutes: Optional[int] = None) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        with self._lock:
            metrics = list(self._metrics)
        
        if last_n_minutes:
            cutoff_time = time.time() - (last_n_minutes * 60)
            metrics = [m for m in metrics if m.timestamp >= cutoff_time]
        
        if not metrics:
            return {"error": "No metrics available"}
        
        # Calculate overall statistics
        total_operations = len(metrics)
        total_time_ms = sum(m.processing_time_ms for m in metrics)
        total_original_tokens = sum(m.original_tokens for m in metrics)
        total_optimized_tokens = sum(m.optimized_tokens for m in metrics)
        cache_hits = sum(1 for m in metrics if m.cache_hit)
        errors = sum(1 for m in metrics if m.error)
        
        # Performance by operation
        operation_performance = {}
        for op in set(m.operation for m in metrics):
            op_metrics = [m for m in metrics if m.operation == op]
            operation_performance[op] = {
                "count": len(op_metrics),
                "avg_time_ms": sum(m.processing_time_ms for m in op_metrics) / len(op_metrics),
                "avg_compression_ratio": sum(m.compression_ratio for m in op_metrics) / len(op_metrics),
                "cache_hit_rate": sum(1 for m in op_metrics if m.cache_hit) / len(op_metrics),
                "error_rate": sum(1 for m in op_metrics if m.error) / len(op_metrics)
            }
        
        # Performance by tool
        tool_performance = {}
        for tool in set(m.tool_name for m in metrics):
            tool_metrics = [m for m in metrics if m.tool_name == tool]
            tool_performance[tool] = {
                "operations": len(tool_metrics),
                "avg_time_ms": sum(m.processing_time_ms for m in tool_metrics) / len(tool_metrics),
                "avg_compression_ratio": sum(m.compression_ratio for m in tool_metrics) / len(tool_metrics),
                "total_tokens_saved": sum(m.original_tokens - m.optimized_tokens for m in tool_metrics)
            }
        
        return {
            "summary": {
                "total_operations": total_operations,
                "total_time_ms": total_time_ms,
                "avg_time_per_operation_ms": total_time_ms / total_operations,
                "total_original_tokens": total_original_tokens,
                "total_optimized_tokens": total_optimized_tokens,
                "overall_compression_ratio": total_optimized_tokens / total_original_tokens if total_original_tokens > 0 else 1.0,
                "cache_hit_rate": cache_hits / total_operations,
                "error_rate": errors / total_operations,
                "tokens_saved": total_original_tokens - total_optimized_tokens
            },
            "by_operation": operation_performance,
            "by_tool": tool_performance,
            "time_period": f"last {last_n_minutes} minutes" if last_n_minutes else "all time"
        }
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get performance optimization recommendations based on collected metrics."""
        recommendations = []
        
        with self._lock:
            if not self._metrics:
                return ["No performance data available for recommendations"]
            
            # Analyze cache hit rates
            total_ops = len(self._metrics)
            cache_hits = sum(1 for m in self._metrics if m.cache_hit)
            cache_hit_rate = cache_hits / total_ops
            
            if cache_hit_rate < 0.3:
                recommendations.append(
                    f"Low cache hit rate ({cache_hit_rate:.1%}). Consider increasing cache size or TTL."
                )
            
            # Analyze processing times
            avg_time = sum(m.processing_time_ms for m in self._metrics) / total_ops
            if avg_time > 100:
                recommendations.append(
                    f"High average processing time ({avg_time:.1f}ms). Consider optimizing content preprocessing."
                )
            
            # Analyze compression ratios
            avg_compression = sum(m.compression_ratio for m in self._metrics) / total_ops
            if avg_compression > 0.8:
                recommendations.append(
                    f"Low compression ratio ({avg_compression:.2f}). Content may not benefit from optimization."
                )
            
            # Analyze error rates
            errors = sum(1 for m in self._metrics if m.error)
            error_rate = errors / total_ops
            if error_rate > 0.05:
                recommendations.append(
                    f"High error rate ({error_rate:.1%}). Check logs for optimization failures."
                )
            
            # Tool-specific recommendations
            for tool_name, stats in self._tool_stats.items():
                if stats["operations"] > 10:  # Only for tools with significant usage
                    if stats["avg_compression_ratio"] > 0.9:
                        recommendations.append(
                            f"Tool '{tool_name}' shows minimal compression benefit. Consider adjusting thresholds."
                        )
        
        if not recommendations:
            recommendations.append("Performance looks good! No specific optimizations recommended.")
        
        return recommendations


# Global performance monitor instance
_performance_monitor: Optional[ContextPerformanceMonitor] = None
_monitor_lock = threading.Lock()


def get_performance_monitor() -> ContextPerformanceMonitor:
    """Get the global context performance monitor instance."""
    global _performance_monitor
    
    with _monitor_lock:
        if _performance_monitor is None:
            _performance_monitor = ContextPerformanceMonitor()
        return _performance_monitor


def record_context_operation(
    operation: str,
    tool_name: str,
    original_tokens: int,
    optimized_tokens: int,
    processing_time_ms: float,
    **kwargs
) -> None:
    """
    Convenience function to record a context management operation.
    
    Args:
        operation: Type of operation ('optimize_file_content', 'optimize_conversation', etc.)
        tool_name: Name of the tool performing the operation
        original_tokens: Original token count before optimization
        optimized_tokens: Token count after optimization
        processing_time_ms: Time taken for the operation in milliseconds
        **kwargs: Additional parameters (cache_hit, strategies_applied, etc.)
    """
    monitor = get_performance_monitor()
    monitor.record_operation(
        operation=operation,
        tool_name=tool_name,
        original_tokens=original_tokens,
        optimized_tokens=optimized_tokens,
        processing_time_ms=processing_time_ms,
        **kwargs
    )


def get_context_performance_summary(last_n_minutes: Optional[int] = None) -> Dict[str, Any]:
    """Get comprehensive context performance summary."""
    monitor = get_performance_monitor()
    return monitor.get_performance_summary(last_n_minutes)


def get_context_optimization_recommendations() -> List[str]:
    """Get performance optimization recommendations."""
    monitor = get_performance_monitor()
    return monitor.get_optimization_recommendations()
