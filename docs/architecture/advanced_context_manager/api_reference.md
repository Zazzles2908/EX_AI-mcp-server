# Advanced Context Manager - API Reference

**Version**: 1.0  
**Date**: 2025-01-13  
**Audience**: Developers integrating Advanced Context Manager

## Core API Functions

### `optimize_for_model()`

General-purpose content optimization for model-specific token limits.

```python
def optimize_for_model(
    content: Union[str, List[Dict[str, Any]]],
    model_context: Optional[Any] = None,
    preserve_conversation_flow: bool = True,
    enable_caching: bool = True
) -> Tuple[Union[str, List[Dict[str, Any]]], Dict[str, Any]]
```

**Parameters**:
- `content`: Content to optimize (string or list of message dictionaries)
- `model_context`: ModelContext instance for token budget calculation
- `preserve_conversation_flow`: Whether to maintain conversation chronology
- `enable_caching`: Whether to use semantic caching

**Returns**: Tuple of (optimized_content, optimization_metadata)

**Example**:
```python
from utils.advanced_context import optimize_for_model

optimized_content, metadata = optimize_for_model(
    content=large_prompt,
    model_context=self._model_context,
    preserve_conversation_flow=True
)

if metadata.get("optimized", False):
    logger.info(f"Compression ratio: {metadata.get('compression_ratio', 1.0):.2f}")
```

### `optimize_file_content()`

Specialized optimization for file content processing.

```python
def optimize_file_content(
    file_content: str,
    file_paths: List[str],
    model_context: Optional[Any] = None,
    context_label: str = "File content"
) -> Tuple[str, Dict[str, Any]]
```

**Parameters**:
- `file_content`: File content string to optimize
- `file_paths`: List of file paths for context
- `model_context`: ModelContext for token allocation
- `context_label`: Descriptive label for optimization context

**Returns**: Tuple of (optimized_content, optimization_metadata)

**Example**:
```python
from utils.advanced_context import optimize_file_content

file_content, _ = self._prepare_file_content_for_prompt(files)
optimized_content, metadata = optimize_file_content(
    file_content=file_content,
    file_paths=files,
    model_context=self._model_context,
    context_label="Code analysis files"
)
```

### `optimize_conversation_thread()`

Optimization for conversation history and thread context.

```python
def optimize_conversation_thread(
    thread_context: Any,
    model_context: Any,
    include_files: bool = True
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]
```

**Parameters**:
- `thread_context`: ThreadContext from conversation memory
- `model_context`: ModelContext for token allocation
- `include_files`: Whether to include file references in optimization

**Returns**: Tuple of (optimized_messages, optimization_metadata)

**Example**:
```python
from utils.advanced_context import optimize_conversation_thread
from utils.conversation_memory import get_thread

thread = get_thread(continuation_id)
optimized_history, metadata = optimize_conversation_thread(
    thread_context=thread,
    model_context=self._model_context,
    include_files=True
)
```

### `optimize_cross_tool_context()`

Optimization for cross-tool context transitions.

```python
def optimize_cross_tool_context(
    current_tool: str,
    previous_tool: str,
    thread_context: Any,
    model_context: Any,
    preserve_tool_transitions: bool = True
) -> Tuple[str, Dict[str, Any]]
```

**Parameters**:
- `current_tool`: Name of the current tool being executed
- `previous_tool`: Name of the previous tool in the conversation
- `thread_context`: ThreadContext from conversation memory
- `model_context`: ModelContext for token allocation
- `preserve_tool_transitions`: Whether to preserve tool transition markers

**Returns**: Tuple of (optimized_context, optimization_metadata)

**Example**:
```python
from utils.advanced_context import optimize_cross_tool_context

optimized_context, metadata = optimize_cross_tool_context(
    current_tool="codereview",
    previous_tool="analyze",
    thread_context=thread,
    model_context=self._model_context
)
```

## Performance Monitoring API

### `get_context_stats()`

Retrieve comprehensive context optimization statistics.

```python
def get_context_stats() -> Dict[str, Any]
```

**Returns**: Dictionary with optimization statistics including:
- `cache_size`: Number of cached optimization results
- `cache_hit_rate`: Percentage of cache hits
- `performance`: Detailed performance metrics
- `timestamp`: When statistics were generated

**Example**:
```python
from utils.advanced_context import get_context_stats

stats = get_context_stats()
logger.info(f"Cache hit rate: {stats.get('cache_hit_rate', 0):.1%}")
logger.info(f"Cache size: {stats.get('cache_size', 0)} entries")
```

### `get_context_performance_recommendations()`

Get actionable optimization recommendations.

```python
def get_context_performance_recommendations() -> List[str]
```

**Returns**: List of optimization recommendations

**Example**:
```python
from utils.advanced_context import get_context_performance_recommendations

recommendations = get_context_performance_recommendations()
for rec in recommendations:
    logger.info(f"Optimization tip: {rec}")
```

### `record_context_operation()`

Record performance metrics for context operations.

```python
def record_context_operation(
    operation: str,
    tool_name: str,
    original_tokens: int,
    optimized_tokens: int,
    processing_time_ms: float,
    **kwargs
) -> None
```

**Parameters**:
- `operation`: Type of operation (e.g., 'optimize_file_content')
- `tool_name`: Name of the tool performing the operation
- `original_tokens`: Token count before optimization
- `optimized_tokens`: Token count after optimization
- `processing_time_ms`: Processing time in milliseconds
- `**kwargs`: Additional parameters (cache_hit, strategies_applied, etc.)

**Example**:
```python
from utils.context_performance import record_context_operation

record_context_operation(
    operation="optimize_file_content",
    tool_name=self.name,
    original_tokens=5000,
    optimized_tokens=3500,
    processing_time_ms=45.2,
    cache_hit=False,
    strategies_applied=["truncation", "compression"]
)
```

## Optimization Metadata

All optimization functions return metadata with the following structure:

```python
{
    "optimized": bool,              # Whether optimization was applied
    "compression_ratio": float,     # Ratio of optimized/original tokens
    "original_tokens": int,         # Original token count
    "optimized_tokens": int,        # Optimized token count
    "strategies_applied": List[str], # Optimization strategies used
    "cache_hit": bool,              # Whether result came from cache
    "processing_time_ms": float,    # Time taken for optimization
    "error": Optional[str]          # Error message if optimization failed
}
```

## Error Handling

All optimization functions implement graceful error handling:

```python
try:
    optimized_content, metadata = optimize_file_content(
        file_content=content,
        file_paths=files,
        model_context=self._model_context
    )
    
    if metadata.get("optimized", False):
        # Use optimized content
        content = optimized_content
    # If not optimized, continue with original content
    
except Exception as e:
    logger.warning(f"Context optimization failed: {e}")
    # Continue with original content - no disruption
```

## Configuration Options

### Optimization Thresholds

Default thresholds can be customized per tool:

```python
# Recommended thresholds by use case
THRESHOLDS = {
    "file_content": 12000,      # General file processing
    "conversation": 15000,      # Conversation history
    "workflow": 10000,          # Workflow processing
    "debug": 8000,              # Debug scenarios
    "analysis": 15000           # Comprehensive analysis
}
```

### Cache Configuration

Cache behavior can be controlled:

```python
# Cache settings (configured in AdvancedContextManager)
CACHE_CONFIG = {
    "max_size": 1000,           # Maximum cache entries
    "ttl_seconds": 3600,        # Time-to-live for cache entries
    "cleanup_interval": 300     # Cache cleanup interval
}
```

## Integration Patterns

### Automatic Integration (Recommended)

Most tools benefit from automatic integration through base classes:

```python
# SimpleTool - automatic file processing optimization
class MyTool(SimpleTool):
    # Optimization applied automatically in _prepare_file_content_for_prompt()
    pass

# WorkflowTool - automatic workflow and cross-tool optimization  
class MyWorkflowTool(WorkflowTool):
    # Multiple optimization points applied automatically
    pass
```

### Manual Integration

For custom optimization needs:

```python
class MyCustomTool(BaseTool):
    def process_large_content(self, content):
        if len(content) > self.optimization_threshold:
            optimized_content, metadata = optimize_for_model(
                content=content,
                model_context=self._model_context
            )
            
            if metadata.get("optimized", False):
                return optimized_content
        
        return content
```

### Conditional Integration

Apply optimization based on conditions:

```python
def conditional_optimization(self, content, files):
    # Only optimize for specific model types
    if self._model_context and "large" in self._model_context.model_name:
        return optimize_file_content(
            file_content=content,
            file_paths=files,
            model_context=self._model_context
        )
    
    return content, {}
```

## Performance Considerations

### When to Optimize

- **File content > 12,000 characters**: Generally beneficial
- **Conversation history > 15,000 characters**: Recommended for continuity
- **Cross-tool transitions**: Always beneficial for context preservation
- **Debug scenarios > 8,000 characters**: Lower threshold for debugging

### When NOT to Optimize

- **Small content < 5,000 characters**: Optimization overhead not worth it
- **Already optimized content**: Check metadata to avoid double-optimization
- **Critical real-time operations**: If latency is more important than token efficiency

### Performance Monitoring

Monitor optimization effectiveness:

```python
# Check performance regularly
stats = get_context_stats()
if stats.get("cache_hit_rate", 0) < 0.3:
    logger.warning("Low cache hit rate - consider adjusting optimization patterns")

if stats.get("avg_compression_ratio", 1.0) > 0.9:
    logger.info("Low compression - content may not benefit from optimization")
```

## Troubleshooting

### Common Issues

1. **No optimization applied**: Check content size against threshold
2. **Poor compression ratio**: Content may not be suitable for optimization
3. **High processing time**: Consider increasing optimization threshold
4. **Cache misses**: Content patterns may be too diverse for effective caching

### Debug Information

Enable debug logging for detailed optimization information:

```python
import logging
logging.getLogger("src.core.agentic.context_manager").setLevel(logging.DEBUG)
logging.getLogger("utils.advanced_context").setLevel(logging.DEBUG)
```

### Performance Analysis

Use the context performance tool for detailed analysis:

```python
from tools.context_performance import ContextPerformanceTool, ContextPerformanceRequest

tool = ContextPerformanceTool()
request = ContextPerformanceRequest(
    time_period_minutes=60,
    include_recommendations=True,
    format="summary"
)

report = await tool.prepare_prompt(request)
print(report)
```

## Version Compatibility

- **Minimum Python Version**: 3.9+
- **Required Dependencies**: pydantic, typing_extensions
- **Optional Dependencies**: prometheus_client (for metrics)

## Migration Notes

### From Legacy Context Management

1. Replace manual token counting with `optimize_for_model()`
2. Replace static truncation with intelligent optimization
3. Add performance monitoring to track improvements
4. Update error handling to use graceful fallback patterns

### Backward Compatibility

All optimization functions are designed to be backward compatible:
- Tools continue working if optimization fails
- Original content is preserved as fallback
- No breaking changes to existing APIs

---

*This API reference covers all public functions and integration patterns for the Advanced Context Manager. For implementation examples, see the Developer Guide.*
