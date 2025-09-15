# Advanced Context Manager - Developer Integration Guide

**Version**: 1.0  
**Date**: 2025-01-13  
**Audience**: EX MCP Server developers and contributors

## Overview

This guide provides comprehensive instructions for integrating the Advanced Context Manager into new and existing tools within the EX MCP Server. The Advanced Context Manager provides intelligent context optimization, semantic caching, and model-aware token management for handling large content efficiently.

## Quick Start

### Basic Integration Pattern

For most tools, integration is as simple as adding a few lines of code:

```python
# In your tool's file processing method
if file_content and len(file_content) > OPTIMIZATION_THRESHOLD:
    try:
        from utils.advanced_context import optimize_file_content
        
        optimized_content, metadata = optimize_file_content(
            file_content=file_content,
            file_paths=file_paths,
            model_context=self._model_context,
            context_label="Tool-specific description"
        )
        
        if metadata.get("optimized", False):
            file_content = optimized_content
            logger.info(f"[CONTEXT_OPTIMIZATION] {self.name}: Optimized content "
                       f"({metadata.get('compression_ratio', 1.0):.2f} compression ratio)")
    except Exception as e:
        logger.warning(f"[CONTEXT_OPTIMIZATION] {self.name}: Failed to optimize: {e}")
        # Continue with original content
```

### Recommended Optimization Thresholds

- **File Content**: 12,000 characters
- **Conversation History**: 15,000 characters  
- **Workflow Content**: 10,000 characters
- **Debug Content**: 8,000 characters (lower threshold for debugging scenarios)

## Integration Patterns by Tool Type

### 1. SimpleTool Integration

For tools inheriting from `SimpleTool`, optimization is often **automatic** through the base class:

```python
class MySimpleTool(SimpleTool):
    def get_name(self) -> str:
        return "my_tool"
    
    # File processing optimization is automatic via _prepare_file_content_for_prompt()
    # No additional integration needed for basic file processing
```

**Automatic Benefits**:
- File content optimization when > 12,000 characters
- Performance monitoring and metrics collection
- Graceful fallback if optimization fails

### 2. WorkflowTool Integration

For tools inheriting from `WorkflowTool`, multiple optimization points are **automatically active**:

```python
class MyWorkflowTool(WorkflowTool):
    def get_name(self) -> str:
        return "my_workflow_tool"
    
    # Automatic optimizations:
    # - Workflow file processing (10,000 char threshold)
    # - Expert analysis content (15,000 char threshold)  
    # - Cross-tool context optimization
    # - Performance monitoring
```

**Automatic Benefits**:
- Multi-step workflow optimization
- Cross-tool context preservation
- Expert analysis optimization
- Performance tracking

### 3. Custom Tool Integration

For custom tools or specialized processing, manual integration provides full control:

```python
class MyCustomTool(BaseTool):
    async def execute(self, request):
        # Custom content processing
        large_content = self.prepare_large_content(request)
        
        # Apply Advanced Context Manager optimization
        if len(large_content) > 10000:
            try:
                from utils.advanced_context import optimize_for_model
                
                optimized_content, metadata = optimize_for_model(
                    content=large_content,
                    model_context=self._model_context,
                    preserve_conversation_flow=True
                )
                
                if metadata.get("optimized", False):
                    large_content = optimized_content
                    self.log_optimization_success(metadata)
                    
            except Exception as e:
                logger.warning(f"Optimization failed: {e}")
        
        return self.process_content(large_content)
```

## Available Integration Functions

### Core Optimization Functions

#### `optimize_file_content()`
**Use Case**: Optimizing file content for tool processing
```python
from utils.advanced_context import optimize_file_content

optimized_content, metadata = optimize_file_content(
    file_content=content,
    file_paths=["file1.py", "file2.py"],
    model_context=self._model_context,
    context_label="Code analysis files"
)
```

#### `optimize_conversation_thread()`
**Use Case**: Optimizing conversation history for continuity
```python
from utils.advanced_context import optimize_conversation_thread

optimized_messages, metadata = optimize_conversation_thread(
    thread_context=thread,
    model_context=self._model_context,
    include_files=True
)
```

#### `optimize_cross_tool_context()`
**Use Case**: Optimizing context for tool transitions
```python
from utils.advanced_context import optimize_cross_tool_context

optimized_context, metadata = optimize_cross_tool_context(
    current_tool="codereview",
    previous_tool="analyze",
    thread_context=thread,
    model_context=self._model_context
)
```

#### `optimize_for_model()`
**Use Case**: General-purpose content optimization
```python
from utils.advanced_context import optimize_for_model

optimized_content, metadata = optimize_for_model(
    content=large_content,
    model_context=self._model_context,
    preserve_conversation_flow=True
)
```

### Performance Monitoring Functions

#### `get_context_stats()`
**Use Case**: Retrieve performance statistics
```python
from utils.advanced_context import get_context_stats

stats = get_context_stats()
logger.info(f"Cache hit rate: {stats.get('cache_hit_rate', 0):.1%}")
```

#### `get_context_performance_recommendations()`
**Use Case**: Get optimization recommendations
```python
from utils.advanced_context import get_context_performance_recommendations

recommendations = get_context_performance_recommendations()
for rec in recommendations:
    logger.info(f"Optimization tip: {rec}")
```

## Integration Best Practices

### 1. Error Handling

Always implement graceful fallback:

```python
try:
    from utils.advanced_context import optimize_file_content
    
    optimized_content, metadata = optimize_file_content(
        file_content=content,
        file_paths=files,
        model_context=self._model_context
    )
    
    if metadata.get("optimized", False):
        content = optimized_content
        logger.info(f"Optimization successful: {metadata.get('compression_ratio', 1.0):.2f} ratio")
    
except Exception as e:
    logger.warning(f"Context optimization failed: {e}")
    # Continue with original content - no disruption to tool functionality
```

### 2. Threshold Selection

Choose appropriate thresholds based on your tool's use case:

```python
# Conservative threshold for critical operations
CRITICAL_THRESHOLD = 8000

# Standard threshold for general processing  
STANDARD_THRESHOLD = 12000

# High threshold for comprehensive analysis
ANALYSIS_THRESHOLD = 15000

if len(content) > STANDARD_THRESHOLD:
    # Apply optimization
```

### 3. Logging and Monitoring

Include optimization metrics in your tool's logging:

```python
if metadata.get("optimized", False):
    logger.info(
        f"[CONTEXT_OPTIMIZATION] {self.name}: "
        f"Optimized {len(file_paths)} files, "
        f"{metadata.get('compression_ratio', 1.0):.2f} compression ratio, "
        f"{len(metadata.get('strategies_applied', []))} strategies applied"
    )
```

### 4. Model Context Integration

Always pass the model context for optimal results:

```python
# Get model context from tool
model_context = getattr(self, '_model_context', None)

# Use in optimization
optimized_content, metadata = optimize_file_content(
    file_content=content,
    file_paths=files,
    model_context=model_context,  # Essential for proper token allocation
    context_label="Tool-specific context"
)
```

## Advanced Integration Patterns

### 1. Custom Optimization Strategies

For specialized content types, you can influence optimization strategies:

```python
# For code-heavy content
optimized_content, metadata = optimize_file_content(
    file_content=code_content,
    file_paths=code_files,
    model_context=self._model_context,
    context_label="Source code analysis"  # Helps optimization choose appropriate strategies
)

# For documentation content
optimized_content, metadata = optimize_file_content(
    file_content=doc_content,
    file_paths=doc_files,
    model_context=self._model_context,
    context_label="Documentation review"  # Different optimization approach
)
```

### 2. Multi-Stage Optimization

For complex workflows, apply optimization at multiple stages:

```python
class ComplexAnalysisTool(WorkflowTool):
    def process_initial_files(self, files):
        # Stage 1: Optimize initial file content
        content, _ = self._prepare_file_content_for_prompt(files)
        
        if len(content) > 12000:
            optimized_content, metadata = optimize_file_content(
                file_content=content,
                file_paths=files,
                model_context=self._model_context,
                context_label="Initial analysis files"
            )
            if metadata.get("optimized", False):
                content = optimized_content
        
        return content
    
    def process_expert_analysis(self, analysis_content, conversation_context):
        # Stage 2: Optimize expert analysis with conversation context
        if len(analysis_content) > 15000:
            optimized_content, metadata = optimize_conversation_thread(
                thread_context=conversation_context,
                model_context=self._model_context,
                include_files=True
            )
            if metadata.get("optimized", False):
                return optimized_content
        
        return analysis_content
```

### 3. Performance-Aware Integration

Monitor and adapt based on performance metrics:

```python
class PerformanceAwareTool(SimpleTool):
    def __init__(self):
        super().__init__()
        self.optimization_threshold = 12000
        self.last_performance_check = 0
    
    def adaptive_optimization(self, content, files):
        # Periodically adjust threshold based on performance
        if time.time() - self.last_performance_check > 300:  # Every 5 minutes
            self.adjust_threshold_based_on_performance()
            self.last_performance_check = time.time()
        
        if len(content) > self.optimization_threshold:
            return self.apply_optimization(content, files)
        
        return content, {}
    
    def adjust_threshold_based_on_performance(self):
        try:
            from utils.advanced_context import get_context_stats
            
            stats = get_context_stats()
            if "performance" in stats:
                perf = stats["performance"]
                if "summary" in perf:
                    avg_time = perf["summary"].get("avg_time_per_operation_ms", 0)
                    
                    # Adjust threshold based on performance
                    if avg_time > 100:  # Slow performance
                        self.optimization_threshold = 15000  # Higher threshold
                    elif avg_time < 50:  # Fast performance
                        self.optimization_threshold = 10000  # Lower threshold
                        
        except Exception as e:
            logger.debug(f"Failed to adjust optimization threshold: {e}")
```

## Testing Your Integration

### 1. Unit Testing

Test optimization integration with various content sizes:

```python
def test_optimization_integration():
    tool = MyTool()
    
    # Test below threshold - no optimization
    small_content = "x" * 5000
    result = tool.process_content(small_content)
    assert "OPTIMIZED" not in result
    
    # Test above threshold - optimization applied
    large_content = "x" * 15000
    result = tool.process_content(large_content)
    # Verify optimization was applied (implementation-specific)
```

### 2. Performance Testing

Validate optimization improves performance:

```python
def test_optimization_performance():
    tool = MyTool()
    large_content = generate_large_test_content()
    
    # Measure without optimization
    start_time = time.time()
    result_without = tool.process_content_without_optimization(large_content)
    time_without = time.time() - start_time
    
    # Measure with optimization
    start_time = time.time()
    result_with = tool.process_content_with_optimization(large_content)
    time_with = time.time() - start_time
    
    # Verify optimization provides benefit
    assert time_with <= time_without * 1.1  # Allow 10% overhead for optimization
```

### 3. Integration Testing

Test with real conversation flows:

```python
def test_conversation_integration():
    # Create conversation thread
    thread_id = create_thread("test_tool", {"test": "data"})
    
    # Add multiple turns
    add_turn(thread_id, "user", "Large user input" * 1000)
    add_turn(thread_id, "assistant", "Large assistant response" * 1000)
    
    # Test tool with conversation context
    tool = MyTool()
    result = tool.execute_with_continuation(request, thread_id)
    
    # Verify conversation context was optimized appropriately
    assert result is not None
    assert "conversation_optimized" in result.metadata
```

## Common Integration Pitfalls

### 1. Missing Error Handling
**Problem**: Not handling optimization failures gracefully
**Solution**: Always wrap optimization calls in try-catch blocks

### 2. Inappropriate Thresholds
**Problem**: Using thresholds that are too low or too high
**Solution**: Start with recommended thresholds and adjust based on performance metrics

### 3. Missing Model Context
**Problem**: Not passing model context to optimization functions
**Solution**: Always pass `self._model_context` when available

### 4. Ignoring Performance Metrics
**Problem**: Not monitoring optimization effectiveness
**Solution**: Use performance monitoring functions to track and improve optimization

### 5. Over-Optimization
**Problem**: Applying optimization to content that doesn't benefit
**Solution**: Use appropriate thresholds and monitor compression ratios

## Migration Guide

### Upgrading Existing Tools

1. **Identify Integration Points**: Look for file processing, content preparation, or prompt building methods
2. **Add Optimization Calls**: Insert optimization calls with appropriate thresholds
3. **Test Thoroughly**: Verify tool functionality is preserved
4. **Monitor Performance**: Use performance monitoring to validate improvements
5. **Adjust Thresholds**: Fine-tune based on actual usage patterns

### Example Migration

**Before**:
```python
def prepare_content(self, files):
    content, _ = self._prepare_file_content_for_prompt(files)
    return content
```

**After**:
```python
def prepare_content(self, files):
    content, _ = self._prepare_file_content_for_prompt(files)
    
    # Add Advanced Context Manager optimization
    if content and len(content) > 12000:
        try:
            from utils.advanced_context import optimize_file_content
            
            optimized_content, metadata = optimize_file_content(
                file_content=content,
                file_paths=files,
                model_context=self._model_context,
                context_label=f"{self.name} file processing"
            )
            
            if metadata.get("optimized", False):
                content = optimized_content
                logger.info(f"[CONTEXT_OPTIMIZATION] {self.name}: Content optimized")
                
        except Exception as e:
            logger.warning(f"[CONTEXT_OPTIMIZATION] {self.name}: Failed to optimize: {e}")
    
    return content
```

## Support and Resources

### Documentation
- **Core Documentation**: `docs/advanced_context_manager.md`
- **Integration Examples**: `docs/advanced_context_manager_integration_summary.md`
- **Performance Guide**: `docs/performance_optimization_monitoring_implementation.md`

### Tools and Utilities
- **Performance Monitoring**: `tools/context_performance.py`
- **Integration Functions**: `utils/advanced_context.py`
- **Core Implementation**: `src/core/agentic/context_manager.py`

### Getting Help
1. **Check Logs**: Look for `[CONTEXT_OPTIMIZATION]` log entries
2. **Monitor Performance**: Use `context_performance` tool for insights
3. **Review Examples**: Study existing integrations in workflow tools
4. **Test Incrementally**: Start with simple integration and expand

## Conclusion

The Advanced Context Manager provides powerful capabilities for handling large content efficiently. By following this guide, you can integrate these capabilities into your tools with minimal effort while maximizing the benefits for users.

**Key Takeaways**:
- Start with automatic integration through base classes
- Add manual optimization for specialized use cases
- Always implement graceful error handling
- Monitor performance and adjust thresholds accordingly
- Test thoroughly to ensure functionality is preserved

The Advanced Context Manager is designed to be **non-intrusive** and **performance-enhancing** - your tools will work better with it, and continue working without it if needed.

---

*For detailed API reference, see `docs/advanced_context_manager_api_reference.md`*
*For performance tuning, see `docs/advanced_context_manager_performance_tuning.md`*
