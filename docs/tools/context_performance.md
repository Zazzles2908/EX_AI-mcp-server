# context_performance - Advanced Context Manager Performance Monitoring

**Category**: Advanced Tools  
**Status**: ✅ Active  
**Added**: 2025-01-13  
**Context Optimization**: N/A (Monitoring Tool)

## Overview

The `context_performance` tool provides comprehensive performance monitoring and optimization recommendations for the Advanced Context Manager system. It offers real-time metrics, performance analytics, and actionable insights to optimize context management operations across all tools.

## Features

### 📊 **Performance Metrics**
- **Processing Time**: Average time per optimization operation
- **Compression Ratios**: Effectiveness of content optimization
- **Cache Performance**: Hit rates and cache utilization statistics
- **Token Efficiency**: Tokens saved through optimization
- **Error Rates**: Failed optimization attempts and fallback usage

### 🎯 **Optimization Recommendations**
- **Intelligent Analysis**: Usage pattern analysis and optimization suggestions
- **Threshold Tuning**: Recommendations for optimization threshold adjustments
- **Cache Optimization**: Cache size and TTL tuning suggestions
- **Performance Alerts**: Identification of performance bottlenecks

### 📈 **Reporting Formats**
- **Summary Reports**: Human-readable performance summaries
- **Detailed Breakdowns**: Per-tool and per-operation analytics
- **JSON Export**: Machine-readable data for external analysis
- **Time-Based Analysis**: Historical performance tracking

## Usage

### Basic Performance Report

```bash
# Get comprehensive performance summary for the last hour
context_performance
```

**Example Output**:
```markdown
# Advanced Context Manager Performance Report

**Analysis Period**: Last 60 minutes
**Generated**: 2025-01-13 15:30:00 UTC

## Performance Summary

- **Total Operations**: 1,247
- **Average Processing Time**: 45.2ms
- **Cache Hit Rate**: 52.3%
- **Overall Compression Ratio**: 0.74
- **Tokens Saved**: 156,890
- **Error Rate**: 0.8%

## Performance by Operation

### optimize_file_content
- Operations: 523
- Avg Time: 38.1ms
- Avg Compression: 0.71
- Cache Hit Rate: 48.2%
- Error Rate: 0.5%

### optimize_conversation_thread
- Operations: 312
- Avg Time: 52.7ms
- Avg Compression: 0.76
- Cache Hit Rate: 58.1%
- Error Rate: 1.2%

## Optimization Recommendations

1. Cache performance is good (52.3%). Consider increasing cache size for better hit rates.
2. Processing times are excellent (<50ms average). No optimization needed.
3. Tool 'debug' shows good compression benefit. Current thresholds are optimal.
```

### Detailed Analysis

```bash
# Get detailed breakdown with recommendations
context_performance --detailed_breakdown=true --include_recommendations=true
```

### Time-Specific Analysis

```bash
# Analyze last 30 minutes
context_performance --time_period_minutes=30

# Analyze all-time performance
context_performance --time_period_minutes=null
```

### JSON Data Export

```bash
# Get machine-readable performance data
context_performance --format=json
```

**Example JSON Output**:
```json
{
  "performance_summary": {
    "total_operations": 1247,
    "total_time_ms": 56389.4,
    "avg_time_per_operation_ms": 45.2,
    "total_original_tokens": 2156890,
    "total_optimized_tokens": 1594567,
    "overall_compression_ratio": 0.74,
    "cache_hit_rate": 0.523,
    "error_rate": 0.008,
    "tokens_saved": 562323
  },
  "by_operation": {
    "optimize_file_content": {
      "count": 523,
      "avg_time_ms": 38.1,
      "avg_compression_ratio": 0.71,
      "cache_hit_rate": 0.482,
      "error_rate": 0.005
    }
  },
  "recommendations": [
    "Cache performance is good (52.3%). Consider increasing cache size for better hit rates.",
    "Processing times are excellent (<50ms average). No optimization needed."
  ]
}
```

## Parameters

### Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `time_period_minutes` | integer | 60 | Time period to analyze (null for all time) |
| `include_recommendations` | boolean | true | Whether to include optimization recommendations |
| `detailed_breakdown` | boolean | true | Whether to include per-tool and per-operation details |
| `format` | string | "summary" | Output format: "summary", "detailed", or "json" |

### Example Requests

```python
# Python API usage
from tools.context_performance import ContextPerformanceTool, ContextPerformanceRequest

tool = ContextPerformanceTool()

# Basic summary
request = ContextPerformanceRequest()
report = await tool.prepare_prompt(request)

# Detailed JSON analysis
request = ContextPerformanceRequest(
    time_period_minutes=120,
    format="json",
    include_recommendations=True
)
data = await tool.prepare_prompt(request)
```

## Performance Insights

### 🎯 **Key Metrics to Monitor**

#### **Processing Time**
- **Excellent**: < 50ms average
- **Good**: 50-100ms average  
- **Needs Attention**: > 100ms average

#### **Compression Ratio**
- **Excellent**: < 0.7 (30%+ reduction)
- **Good**: 0.7-0.8 (20-30% reduction)
- **Acceptable**: 0.8-0.9 (10-20% reduction)
- **Poor**: > 0.9 (< 10% reduction)

#### **Cache Hit Rate**
- **Excellent**: > 70%
- **Good**: 50-70%
- **Acceptable**: 30-50%
- **Poor**: < 30%

#### **Error Rate**
- **Excellent**: < 1%
- **Acceptable**: 1-5%
- **Needs Attention**: > 5%

### 📊 **Performance Patterns**

#### **High Cache Hit Rates**
Indicates:
- Consistent content patterns
- Effective caching strategy
- Good optimization threshold settings

#### **Low Compression Ratios**
May indicate:
- Content already optimized
- Inappropriate optimization thresholds
- Content type not suitable for optimization

#### **High Processing Times**
May indicate:
- Content too large for efficient processing
- System resource constraints
- Need for threshold adjustment

## Troubleshooting

### Common Issues

#### **No Performance Data**
```bash
# Check if Advanced Context Manager is active
context_performance --time_period_minutes=1440  # Last 24 hours
```

If no data is available, ensure:
1. Advanced Context Manager is integrated
2. Tools are processing content above optimization thresholds
3. Performance monitoring is enabled

#### **Poor Performance Metrics**
```bash
# Get detailed recommendations
context_performance --include_recommendations=true --detailed_breakdown=true
```

Common solutions:
1. **High processing time**: Increase optimization thresholds
2. **Low cache hit rate**: Increase cache size or TTL
3. **Poor compression**: Adjust thresholds or review content types

#### **Missing Tool Data**
Some tools may not appear in metrics if:
1. They haven't processed content above thresholds
2. They don't use Advanced Context Manager integration
3. They've had no activity in the specified time period

## Integration with Other Tools

### 📈 **Performance Monitoring Workflow**

```bash
# 1. Check overall system performance
context_performance --format=summary

# 2. Get detailed analysis for optimization
context_performance --detailed_breakdown=true

# 3. Export data for external analysis
context_performance --format=json > performance_data.json

# 4. Monitor specific time periods
context_performance --time_period_minutes=30  # Last 30 minutes
```

### 🔧 **Performance Tuning Workflow**

1. **Baseline Measurement**: Run `context_performance` to establish baseline
2. **Identify Issues**: Review recommendations and performance patterns
3. **Apply Optimizations**: Adjust thresholds, cache settings, etc.
4. **Measure Impact**: Run `context_performance` again to validate improvements
5. **Iterate**: Repeat process for continuous optimization

## Advanced Usage

### 📊 **Performance Dashboard Integration**

The JSON output can be integrated with monitoring dashboards:

```python
import json
import requests

# Get performance data
performance_data = await context_performance_tool.prepare_prompt(
    ContextPerformanceRequest(format="json")
)

# Send to monitoring system
data = json.loads(performance_data)
requests.post("https://monitoring.example.com/metrics", json=data)
```

### 🚨 **Automated Alerting**

```python
# Check for performance issues
performance_data = json.loads(await tool.prepare_prompt(request))
summary = performance_data["performance_summary"]

if summary["avg_time_per_operation_ms"] > 100:
    send_alert("High processing time detected")

if summary["cache_hit_rate"] < 0.3:
    send_alert("Low cache hit rate detected")

if summary["error_rate"] > 0.05:
    send_alert("High error rate detected")
```

### 📈 **Historical Tracking**

```bash
# Daily performance tracking
context_performance --time_period_minutes=1440 --format=json > daily_$(date +%Y%m%d).json

# Weekly performance summary
context_performance --time_period_minutes=10080 --format=summary > weekly_report.md
```

## Related Documentation

- **[Advanced Context Manager](../architecture/advanced_context_manager/README.md)** - Complete system overview
- **[Performance Tuning Guide](../architecture/advanced_context_manager/performance_tuning.md)** - Optimization strategies
- **[API Reference](../architecture/advanced_context_manager/api_reference.md)** - Technical implementation details

---

*The context_performance tool provides essential insights for optimizing the Advanced Context Manager system, ensuring optimal performance across all 25 tools in the EX MCP Server.*
