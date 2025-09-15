"""
Context Performance Monitoring Tool

Provides comprehensive performance monitoring and optimization recommendations
for Advanced Context Manager operations across the EX MCP Server.
"""
from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from tools.simple.base import SimpleTool


class ContextPerformanceRequest(BaseModel):
    """Request model for context performance monitoring."""
    
    time_period_minutes: Optional[int] = Field(
        default=60,
        description="Time period in minutes to analyze (default: 60 minutes, None for all time)"
    )
    include_recommendations: bool = Field(
        default=True,
        description="Whether to include optimization recommendations"
    )
    detailed_breakdown: bool = Field(
        default=True,
        description="Whether to include detailed breakdown by operation and tool"
    )
    format: str = Field(
        default="summary",
        description="Output format: 'summary', 'detailed', or 'json'"
    )


class ContextPerformanceTool(SimpleTool):
    """
    Context Performance Monitoring Tool
    
    Provides comprehensive performance monitoring and optimization recommendations
    for Advanced Context Manager operations. Shows metrics like cache hit rates,
    compression ratios, processing times, and identifies optimization opportunities.
    """
    
    def get_name(self) -> str:
        return "context_performance"
    
    def get_description(self) -> str:
        return (
            "Monitor Advanced Context Manager performance and get optimization recommendations. "
            "Shows cache hit rates, compression ratios, processing times, and identifies "
            "performance bottlenecks across all context management operations."
        )
    
    def get_request_model(self):
        return ContextPerformanceRequest

    def get_tool_fields(self) -> List[str]:
        """Return the fields that this tool uses from the request."""
        return ["time_period_minutes", "include_recommendations", "detailed_breakdown", "format"]
    
    async def prepare_prompt(self, request: ContextPerformanceRequest) -> str:
        """Prepare the performance monitoring analysis."""
        try:
            from utils.advanced_context import get_context_stats, get_context_performance_recommendations
            from utils.context_performance import get_context_performance_summary
            
            # Get comprehensive performance data
            time_period = request.time_period_minutes
            performance_summary = get_context_performance_summary(time_period)
            context_stats = get_context_stats()
            
            if request.format == "json":
                # Return raw JSON data
                result_data = {
                    "performance_summary": performance_summary,
                    "context_stats": context_stats,
                    "time_period_minutes": time_period
                }
                
                if request.include_recommendations:
                    result_data["recommendations"] = get_context_performance_recommendations()
                
                return json.dumps(result_data, indent=2)
            
            # Build formatted report
            report_lines = [
                "# Advanced Context Manager Performance Report",
                "",
                f"**Analysis Period**: {f'Last {time_period} minutes' if time_period else 'All time'}",
                f"**Generated**: {self._get_current_timestamp()}",
                ""
            ]
            
            # Performance Summary
            if "summary" in performance_summary:
                summary = performance_summary["summary"]
                report_lines.extend([
                    "## Performance Summary",
                    "",
                    f"- **Total Operations**: {summary.get('total_operations', 0):,}",
                    f"- **Average Processing Time**: {summary.get('avg_time_per_operation_ms', 0):.1f}ms",
                    f"- **Cache Hit Rate**: {summary.get('cache_hit_rate', 0):.1%}",
                    f"- **Overall Compression Ratio**: {summary.get('overall_compression_ratio', 1.0):.2f}",
                    f"- **Tokens Saved**: {summary.get('tokens_saved', 0):,}",
                    f"- **Error Rate**: {summary.get('error_rate', 0):.1%}",
                    ""
                ])
            
            # Detailed Breakdown
            if request.detailed_breakdown and "by_operation" in performance_summary:
                report_lines.extend([
                    "## Performance by Operation",
                    ""
                ])
                
                for operation, stats in performance_summary["by_operation"].items():
                    report_lines.extend([
                        f"### {operation}",
                        f"- Operations: {stats.get('count', 0):,}",
                        f"- Avg Time: {stats.get('avg_time_ms', 0):.1f}ms",
                        f"- Avg Compression: {stats.get('avg_compression_ratio', 1.0):.2f}",
                        f"- Cache Hit Rate: {stats.get('cache_hit_rate', 0):.1%}",
                        f"- Error Rate: {stats.get('error_rate', 0):.1%}",
                        ""
                    ])
                
                # Tool Performance
                if "by_tool" in performance_summary:
                    report_lines.extend([
                        "## Performance by Tool",
                        ""
                    ])
                    
                    for tool, stats in performance_summary["by_tool"].items():
                        report_lines.extend([
                            f"### {tool}",
                            f"- Operations: {stats.get('operations', 0):,}",
                            f"- Avg Time: {stats.get('avg_time_ms', 0):.1f}ms",
                            f"- Avg Compression: {stats.get('avg_compression_ratio', 1.0):.2f}",
                            f"- Tokens Saved: {stats.get('total_tokens_saved', 0):,}",
                            ""
                        ])
            
            # Context Manager Stats
            if "cache_size" in context_stats:
                report_lines.extend([
                    "## Context Manager Statistics",
                    "",
                    f"- **Cache Size**: {context_stats.get('cache_size', 0)} entries",
                    f"- **Cache Max Size**: {context_stats.get('cache_max_size', 0)}",
                    f"- **Cache TTL**: {context_stats.get('cache_ttl_seconds', 0)} seconds",
                    f"- **Total Cache Accesses**: {context_stats.get('total_accesses', 0):,}",
                    f"- **Avg Accesses per Entry**: {context_stats.get('average_accesses_per_entry', 0):.1f}",
                    ""
                ])
            
            # Optimization Recommendations
            if request.include_recommendations:
                recommendations = get_context_performance_recommendations()
                if recommendations:
                    report_lines.extend([
                        "## Optimization Recommendations",
                        ""
                    ])
                    
                    for i, rec in enumerate(recommendations, 1):
                        report_lines.append(f"{i}. {rec}")
                    
                    report_lines.append("")
            
            # Performance Insights
            if "summary" in performance_summary:
                summary = performance_summary["summary"]
                insights = []
                
                # Generate insights based on metrics
                if summary.get('cache_hit_rate', 0) > 0.7:
                    insights.append("✅ Excellent cache performance - most operations benefit from caching")
                elif summary.get('cache_hit_rate', 0) > 0.4:
                    insights.append("⚠️ Moderate cache performance - consider increasing cache size")
                else:
                    insights.append("❌ Low cache performance - optimization patterns may be too diverse")
                
                if summary.get('overall_compression_ratio', 1.0) < 0.7:
                    insights.append("✅ Good compression achieved - content is being optimized effectively")
                elif summary.get('overall_compression_ratio', 1.0) < 0.9:
                    insights.append("⚠️ Moderate compression - some content may not benefit from optimization")
                else:
                    insights.append("❌ Low compression - consider adjusting optimization thresholds")
                
                if summary.get('avg_time_per_operation_ms', 0) < 50:
                    insights.append("✅ Fast processing times - optimization is efficient")
                elif summary.get('avg_time_per_operation_ms', 0) < 100:
                    insights.append("⚠️ Moderate processing times - acceptable performance")
                else:
                    insights.append("❌ Slow processing times - consider performance optimization")
                
                if insights:
                    report_lines.extend([
                        "## Performance Insights",
                        ""
                    ])
                    for insight in insights:
                        report_lines.append(f"- {insight}")
                    report_lines.append("")
            
            # Footer
            report_lines.extend([
                "---",
                "",
                "*This report was generated by the Context Performance Monitoring Tool.*",
                "*Use `format: 'json'` for machine-readable output.*"
            ])
            
            return "\n".join(report_lines)
            
        except Exception as e:
            return f"Error generating performance report: {str(e)}"
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp for report generation."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    def get_system_prompt(self) -> str:
        return (
            "You are a context performance monitoring assistant. You analyze Advanced Context Manager "
            "performance metrics and provide insights about optimization effectiveness, cache performance, "
            "and processing efficiency. Focus on actionable insights and clear performance summaries."
        )
    
    def get_default_temperature(self) -> float:
        return 0.1  # Low temperature for consistent, factual reporting
