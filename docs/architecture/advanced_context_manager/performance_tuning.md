# Advanced Context Manager - Performance Tuning Guide

**Version**: 1.0  
**Date**: 2025-01-13  
**Audience**: System administrators and performance engineers

## Overview

This guide provides comprehensive instructions for tuning the Advanced Context Manager for optimal performance in production environments. It covers threshold optimization, cache tuning, monitoring setup, and troubleshooting performance issues.

## Performance Metrics Overview

### Key Performance Indicators (KPIs)

1. **Processing Time**: Average time per optimization operation
2. **Compression Ratio**: Effectiveness of content optimization (lower is better)
3. **Cache Hit Rate**: Percentage of operations served from cache
4. **Token Efficiency**: Tokens saved through optimization
5. **Error Rate**: Percentage of failed optimization attempts

### Target Performance Benchmarks

- **Processing Time**: < 50ms per operation (excellent), < 100ms (acceptable)
- **Compression Ratio**: < 0.7 (excellent), < 0.8 (good), < 0.9 (acceptable)
- **Cache Hit Rate**: > 70% (excellent), > 50% (good), > 30% (acceptable)
- **Error Rate**: < 1% (excellent), < 5% (acceptable)

## Optimization Threshold Tuning

### Default Thresholds

```python
DEFAULT_THRESHOLDS = {
    "file_content": 12000,      # Base tool file processing
    "conversation": 15000,      # Conversation history
    "workflow": 10000,          # Workflow processing
    "expert_analysis": 15000,   # Expert analysis content
    "debug": 8000,              # Debug scenarios
    "cross_tool": 5000          # Cross-tool context
}
```

### Threshold Optimization Strategy

#### 1. Monitor Current Performance

```python
from utils.advanced_context import get_context_stats

stats = get_context_stats()
performance = stats.get("performance", {})

if "by_operation" in performance:
    for operation, metrics in performance["by_operation"].items():
        avg_time = metrics.get("avg_time_ms", 0)
        compression = metrics.get("avg_compression_ratio", 1.0)
        
        print(f"{operation}:")
        print(f"  Average time: {avg_time:.1f}ms")
        print(f"  Compression ratio: {compression:.2f}")
```

#### 2. Adjust Thresholds Based on Performance

**High Processing Time (> 100ms)**:
- Increase thresholds by 20-50%
- Reduce optimization frequency for marginal content

**Low Compression Ratio (> 0.9)**:
- Increase thresholds to focus on content that benefits more
- Consider disabling optimization for specific content types

**High Cache Miss Rate (< 30%)**:
- Lower thresholds to increase optimization frequency
- More operations = better cache utilization

### Dynamic Threshold Adjustment

Implement adaptive thresholds based on real-time performance:

```python
class AdaptiveThresholdManager:
    def __init__(self):
        self.base_threshold = 12000
        self.adjustment_factor = 1.0
        self.last_adjustment = time.time()
    
    def get_current_threshold(self):
        return int(self.base_threshold * self.adjustment_factor)
    
    def adjust_based_on_performance(self):
        if time.time() - self.last_adjustment < 300:  # Adjust every 5 minutes
            return
        
        stats = get_context_stats()
        if "performance" in stats and "summary" in stats["performance"]:
            summary = stats["performance"]["summary"]
            avg_time = summary.get("avg_time_per_operation_ms", 0)
            
            if avg_time > 100:  # Too slow
                self.adjustment_factor *= 1.2  # Increase threshold
            elif avg_time < 30:  # Very fast
                self.adjustment_factor *= 0.9  # Decrease threshold
            
            self.adjustment_factor = max(0.5, min(2.0, self.adjustment_factor))
            self.last_adjustment = time.time()
```

## Cache Performance Tuning

### Cache Configuration

The Advanced Context Manager uses semantic caching with configurable parameters:

```python
CACHE_CONFIG = {
    "max_size": 1000,           # Maximum number of cached entries
    "ttl_seconds": 3600,        # Time-to-live for cache entries (1 hour)
    "cleanup_interval": 300     # Cache cleanup interval (5 minutes)
}
```

### Cache Optimization Strategies

#### 1. Cache Size Tuning

**Monitor cache utilization**:
```python
stats = get_context_stats()
cache_size = stats.get("cache_size", 0)
max_cache_size = stats.get("cache_max_size", 1000)
utilization = cache_size / max_cache_size if max_cache_size > 0 else 0

print(f"Cache utilization: {utilization:.1%}")
```

**Optimization guidelines**:
- **High utilization (> 90%)**: Increase cache size
- **Low utilization (< 50%)**: Consider reducing cache size to save memory
- **Frequent evictions**: Increase cache size or reduce TTL

#### 2. TTL Optimization

**Short TTL (< 1 hour)**:
- Better for rapidly changing content
- Higher cache miss rate but fresher results

**Long TTL (> 4 hours)**:
- Better for stable content patterns
- Higher cache hit rate but potentially stale results

**Adaptive TTL**:
```python
def calculate_adaptive_ttl(content_type, usage_pattern):
    base_ttl = 3600  # 1 hour
    
    if content_type == "file_content":
        return base_ttl * 2  # Files change less frequently
    elif content_type == "conversation":
        return base_ttl // 2  # Conversations are more dynamic
    elif usage_pattern == "frequent":
        return base_ttl * 3  # Keep frequently used content longer
    
    return base_ttl
```

### Cache Performance Monitoring

Set up alerts for cache performance issues:

```python
def monitor_cache_performance():
    stats = get_context_stats()
    
    cache_hit_rate = stats.get("cache_hit_rate", 0)
    if cache_hit_rate < 0.3:
        logger.warning(f"Low cache hit rate: {cache_hit_rate:.1%}")
        # Consider: increasing cache size, adjusting TTL, or reviewing content patterns
    
    avg_accesses = stats.get("average_accesses_per_entry", 0)
    if avg_accesses < 2:
        logger.info(f"Low cache reuse: {avg_accesses:.1f} accesses per entry")
        # Consider: reducing cache size or shortening TTL
```

## Model-Specific Optimization

### Token Allocation Tuning

Different models have different optimal token allocation strategies:

```python
MODEL_OPTIMIZATIONS = {
    "gpt-4": {
        "content_ratio": 0.7,       # 70% for content
        "history_ratio": 0.2,       # 20% for history
        "reserve_ratio": 0.1        # 10% reserve
    },
    "claude-3": {
        "content_ratio": 0.8,       # Claude handles more content well
        "history_ratio": 0.15,
        "reserve_ratio": 0.05
    },
    "gemini-pro": {
        "content_ratio": 0.6,       # More conservative
        "history_ratio": 0.25,
        "reserve_ratio": 0.15
    }
}
```

### Model-Aware Threshold Adjustment

```python
def get_model_specific_threshold(model_name, base_threshold):
    model_factors = {
        "gpt-4": 1.2,           # Can handle more content
        "claude-3": 1.3,        # Excellent with large contexts
        "gemini-pro": 0.9,      # More conservative
        "gpt-3.5": 0.8          # Smaller context window
    }
    
    factor = model_factors.get(model_name, 1.0)
    return int(base_threshold * factor)
```

## Performance Monitoring Setup

### Real-Time Monitoring

Set up continuous performance monitoring:

```python
import time
import threading
from utils.advanced_context import get_context_stats

class PerformanceMonitor:
    def __init__(self, interval=300):  # 5 minutes
        self.interval = interval
        self.running = False
        self.thread = None
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.start()
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
    
    def _monitor_loop(self):
        while self.running:
            try:
                self._check_performance()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
    
    def _check_performance(self):
        stats = get_context_stats()
        
        if "performance" in stats and "summary" in stats["performance"]:
            summary = stats["performance"]["summary"]
            
            # Check processing time
            avg_time = summary.get("avg_time_per_operation_ms", 0)
            if avg_time > 100:
                logger.warning(f"High processing time: {avg_time:.1f}ms")
            
            # Check compression ratio
            compression = summary.get("overall_compression_ratio", 1.0)
            if compression > 0.9:
                logger.info(f"Low compression efficiency: {compression:.2f}")
            
            # Check error rate
            error_rate = summary.get("error_rate", 0)
            if error_rate > 0.05:
                logger.error(f"High error rate: {error_rate:.1%}")
```

### Performance Alerts

Configure alerts for performance degradation:

```python
ALERT_THRESHOLDS = {
    "max_processing_time_ms": 150,
    "min_cache_hit_rate": 0.25,
    "max_error_rate": 0.05,
    "min_compression_ratio": 0.95  # Alert if compression is very poor
}

def check_performance_alerts():
    stats = get_context_stats()
    alerts = []
    
    if "performance" in stats and "summary" in stats["performance"]:
        summary = stats["performance"]["summary"]
        
        avg_time = summary.get("avg_time_per_operation_ms", 0)
        if avg_time > ALERT_THRESHOLDS["max_processing_time_ms"]:
            alerts.append(f"High processing time: {avg_time:.1f}ms")
        
        cache_hit_rate = summary.get("cache_hit_rate", 0)
        if cache_hit_rate < ALERT_THRESHOLDS["min_cache_hit_rate"]:
            alerts.append(f"Low cache hit rate: {cache_hit_rate:.1%}")
        
        error_rate = summary.get("error_rate", 0)
        if error_rate > ALERT_THRESHOLDS["max_error_rate"]:
            alerts.append(f"High error rate: {error_rate:.1%}")
    
    return alerts
```

## Troubleshooting Performance Issues

### Common Performance Problems

#### 1. High Processing Time

**Symptoms**: Average processing time > 100ms
**Causes**:
- Content too large for efficient processing
- Complex optimization strategies
- System resource constraints

**Solutions**:
```python
# Increase optimization thresholds
INCREASED_THRESHOLDS = {
    "file_content": 15000,      # Was 12000
    "conversation": 20000,      # Was 15000
    "workflow": 12000           # Was 10000
}

# Simplify optimization strategies
SIMPLIFIED_STRATEGIES = [
    "intelligent_truncation",   # Keep only essential strategies
    "preserve_structure"        # Remove complex compression
]
```

#### 2. Low Cache Hit Rate

**Symptoms**: Cache hit rate < 30%
**Causes**:
- Content patterns too diverse
- Cache size too small
- TTL too short

**Solutions**:
```python
# Increase cache size
CACHE_CONFIG["max_size"] = 2000  # Was 1000

# Increase TTL
CACHE_CONFIG["ttl_seconds"] = 7200  # Was 3600 (2 hours)

# Implement content normalization for better cache hits
def normalize_content_for_caching(content):
    # Remove timestamps, user-specific data, etc.
    normalized = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', '[TIMESTAMP]', content)
    normalized = re.sub(r'user_\d+', '[USER]', normalized)
    return normalized
```

#### 3. Poor Compression Ratio

**Symptoms**: Compression ratio > 0.9 (little optimization benefit)
**Causes**:
- Content already optimized
- Content type not suitable for optimization
- Thresholds too low

**Solutions**:
```python
# Increase thresholds to focus on content that benefits more
SELECTIVE_THRESHOLDS = {
    "file_content": 20000,      # Only optimize very large content
    "conversation": 25000,
    "workflow": 15000
}

# Add content type detection
def should_optimize_content(content, content_type):
    if content_type == "code":
        return len(content) > 15000  # Code compresses well
    elif content_type == "documentation":
        return len(content) > 10000  # Docs have redundancy
    elif content_type == "logs":
        return len(content) > 5000   # Logs are very repetitive
    else:
        return len(content) > 20000  # Conservative for unknown types
```

### Performance Debugging

Enable detailed performance logging:

```python
import logging

# Enable debug logging for performance analysis
logging.getLogger("src.core.agentic.context_manager").setLevel(logging.DEBUG)
logging.getLogger("utils.context_performance").setLevel(logging.DEBUG)

# Add performance timing to your tools
import time

def timed_optimization(content, files, model_context):
    start_time = time.time()
    
    try:
        optimized_content, metadata = optimize_file_content(
            file_content=content,
            file_paths=files,
            model_context=model_context
        )
        
        processing_time = (time.time() - start_time) * 1000
        logger.debug(f"Optimization took {processing_time:.1f}ms")
        
        return optimized_content, metadata
        
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        logger.error(f"Optimization failed after {processing_time:.1f}ms: {e}")
        raise
```

## Production Deployment Recommendations

### Resource Allocation

**Memory Requirements**:
- Base: 100MB for context manager
- Cache: ~1MB per 1000 cache entries
- Monitoring: ~50MB for performance tracking

**CPU Requirements**:
- Optimization: ~10-50ms CPU time per operation
- Cache management: Minimal CPU overhead
- Monitoring: ~1% CPU overhead

### Configuration for Different Environments

#### Development Environment
```python
DEV_CONFIG = {
    "optimization_thresholds": {
        "file_content": 8000,       # Lower thresholds for testing
        "conversation": 10000,
        "workflow": 6000
    },
    "cache_config": {
        "max_size": 500,            # Smaller cache
        "ttl_seconds": 1800         # 30 minutes
    },
    "monitoring_interval": 60       # Check every minute
}
```

#### Production Environment
```python
PROD_CONFIG = {
    "optimization_thresholds": {
        "file_content": 12000,      # Standard thresholds
        "conversation": 15000,
        "workflow": 10000
    },
    "cache_config": {
        "max_size": 2000,           # Larger cache
        "ttl_seconds": 7200         # 2 hours
    },
    "monitoring_interval": 300      # Check every 5 minutes
}
```

#### High-Volume Environment
```python
HIGH_VOLUME_CONFIG = {
    "optimization_thresholds": {
        "file_content": 15000,      # Higher thresholds
        "conversation": 20000,
        "workflow": 12000
    },
    "cache_config": {
        "max_size": 5000,           # Much larger cache
        "ttl_seconds": 14400        # 4 hours
    },
    "monitoring_interval": 600      # Check every 10 minutes
}
```

## Conclusion

Effective performance tuning of the Advanced Context Manager requires:

1. **Continuous monitoring** of key performance metrics
2. **Adaptive threshold adjustment** based on usage patterns
3. **Cache optimization** for your specific content patterns
4. **Model-specific tuning** for optimal results
5. **Proactive alerting** for performance degradation

Regular performance reviews and adjustments ensure the Advanced Context Manager continues to provide optimal performance as usage patterns evolve.

---

*For implementation details, see the Developer Guide and API Reference.*
