> DEPRECATED (Phase A): Legacy guidance kept for history. Prefer the canonical docs:
> - docs/alignment/phaseA/* (current plan and supersessions)
> - docs/architecture/* (canonical design)
> See docs/alignment/phaseA/SCRIPTS_SUPERSESSION.md for preferred entry points.


# Auggie CLI: Systematic EXAI MCP Server Repair Instructions

## Overview

This document provides comprehensive instructions for using the exai MCP tool to systematically repair all issues identified in the EX_AI MCP server assessment. The repository is located at: https://github.com/Zazzles2908/EX_AI-mcp-server

## Important Notes

1. **Self-Analysis Consideration**: You are using exai to analyze and fix exai itself. Be aware of potential recursion issues.
2. **Broken Consensus Tool**: The consensus tool is completely non-functional due to Pydantic validation errors. Do not rely on it until fixed.
3. **Sequential Execution**: Follow the phases in order - each phase builds on the previous one.
4. **Validation After Each Phase**: Use exai's precommit tool to validate changes before proceeding.

## Phase 1: Critical Infrastructure Repair

### 1.1 Fix Consensus Tool (CRITICAL - BLOCKING)

**Issue**: Complete failure due to Pydantic validation schema mismatch
**Error**: `1 validation error for ConsensusRequest findings Field required`

```bash
# Use debug workflow to investigate the consensus tool validation issue
exai debug --target "consensus tool validation error" \
    --focus "Pydantic ConsensusRequest model schema" \
    --investigation_depth "deep" \
    --include_dependencies true \
    --output_format "structured"

# After identifying the root cause, use refactor workflow to fix
exai refactor --target "consensus tool Pydantic models" \
    --refactor_type "fix_validation_schema" \
    --scope "consensus tool only" \
    --preserve_api true \
    --test_coverage true
```

### 1.2 Fix Assessment Infrastructure

**Issue**: JSON parsing failures, incomplete file examination, low confidence reporting

```bash
# Debug assessment infrastructure issues
exai debug --target "assessment infrastructure failures" \
    --focus "JSON parsing and file examination process" \
    --investigation_depth "comprehensive" \
    --trace_execution true

# Refactor assessment system
exai refactor --target "assessment infrastructure" \
    --refactor_type "fix_parsing_and_examination" \
    --scope "assessment system" \
    --maintain_backwards_compatibility true
```

### 1.3 Validate Critical Fixes

```bash
# Test the consensus tool specifically
exai testgen --target "consensus tool" \
    --test_types "unit,integration,validation" \
    --coverage_threshold 90 \
    --include_error_cases true

# Run precommit validation
exai precommit --scope "critical_fixes" \
    --include_tests true \
    --security_scan true
```

## Phase 2: Security Vulnerability Remediation

### 2.1 Security Audit

```bash
# Comprehensive security audit
exai secaudit --scope "entire_codebase" \
    --focus_areas "file_path_validation,input_sanitization,directory_traversal" \
    --severity_threshold "medium" \
    --include_recommendations true \
    --output_format "detailed"
```

### 2.2 Fix File Path Security Issues

**Issue**: Chat tool accepts absolute paths without validation (directory traversal risk)

```bash
# Debug file path security vulnerabilities
exai debug --target "file path security vulnerabilities" \
    --focus "chat tool file handling" \
    --investigation_depth "security_focused" \
    --include_attack_vectors true

# Refactor to add proper path validation
exai refactor --target "file path validation" \
    --refactor_type "security_hardening" \
    --scope "chat tool and related file handlers" \
    --security_first true \
    --add_input_validation true
```

### 2.3 Fix Input Size and Type Validation

**Issue**: No size caps on files/images, unbounded input risk

```bash
# Refactor input validation across all tools
exai refactor --target "input validation system" \
    --refactor_type "add_comprehensive_validation" \
    --scope "all_user_facing_tools" \
    --include_size_limits true \
    --include_type_validation true \
    --add_sanitization true
```

### 2.4 Validate Security Fixes

```bash
# Generate security-focused tests
exai testgen --target "security_fixes" \
    --test_types "security,penetration,boundary" \
    --include_attack_scenarios true \
    --coverage_threshold 95

# Run security audit again to verify fixes
exai secaudit --scope "security_fixes" \
    --compare_baseline true \
    --verify_mitigations true
```

## Phase 3: Performance and Reliability Issues

### 3.1 Analyze Performance Bottlenecks

```bash
# Comprehensive performance analysis
exai analyze --target "performance_bottlenecks" \
    --analysis_type "performance" \
    --focus_areas "large_file_handling,subprocess_calls,memory_usage" \
    --include_profiling true \
    --depth "comprehensive"
```

### 3.2 Fix Activity Tool Performance Issues

**Issue**: Brittle log-path assumptions, no time-window filtering, raw text output

```bash
# Debug activity tool reliability issues
exai debug --target "activity tool reliability" \
    --focus "log rotation handling and performance" \
    --investigation_depth "comprehensive" \
    --include_edge_cases true

# Refactor activity tool for reliability and performance
exai refactor --target "activity tool" \
    --refactor_type "reliability_and_performance" \
    --improvements "flexible_log_paths,time_filtering,structured_output,reverse_seek_tailing" \
    --maintain_api_compatibility true
```

### 3.3 Fix Analyze Tool Performance Issues

**Issue**: Configuration overengineering, brittle step validation, forced workflow anti-pattern

```bash
# Refactor analyze tool for simplicity and performance
exai refactor --target "analyze tool" \
    --refactor_type "simplification_and_optimization" \
    --improvements "reduce_configuration_complexity,flexible_workflows,timeout_handling" \
    --preserve_core_functionality true \
    --progressive_disclosure true
```

### 3.4 Optimize Subprocess Handling

**Issue**: Git subprocess calls without timeout handling across multiple tools

```bash
# Refactor subprocess handling across all tools
exai refactor --target "subprocess_handling" \
    --refactor_type "reliability_improvement" \
    --scope "all_tools_with_subprocess_calls" \
    --add_timeouts true \
    --add_error_handling true \
    --add_retry_logic true
```

## Phase 4: Architectural Improvements

### 4.1 Schema Management Consolidation

**Issue**: Manual schema overrides, field description duplication, validation inconsistencies

```bash
# Analyze schema management patterns
exai analyze --target "schema_management_architecture" \
    --analysis_type "architectural" \
    --focus_areas "schema_duplication,validation_patterns,configuration_management" \
    --depth "comprehensive"

# Refactor schema management system
exai refactor --target "schema_management" \
    --refactor_type "architectural_consolidation" \
    --create_shared_patterns true \
    --eliminate_duplication true \
    --standardize_validation true
```

### 4.2 Error Handling Standardization

**Issue**: Generic exception catching, user-unfriendly error messages

```bash
# Refactor error handling across all tools
exai refactor --target "error_handling_system" \
    --refactor_type "standardization" \
    --scope "all_tools" \
    --create_error_hierarchy true \
    --add_user_friendly_messages true \
    --structured_error_responses true
```

### 4.3 Tool Architecture Optimization

**Issue**: Over-engineering, inheritance misuse, schema duplication

```bash
# Analyze tool architecture patterns
exai analyze --target "tool_architecture" \
    --analysis_type "architectural" \
    --focus_areas "inheritance_patterns,composition_opportunities,base_class_design" \
    --depth "comprehensive"

# Refactor tool architecture
exai refactor --target "tool_architecture" \
    --refactor_type "architectural_improvement" \
    --use_composition_over_inheritance true \
    --create_specialized_base_classes true \
    --eliminate_unnecessary_complexity true
```

## Phase 5: Code Quality and Maintainability

### 5.1 Comprehensive Code Review

```bash
# Perform comprehensive code review
exai codereview --scope "entire_codebase" \
    --focus_areas "maintainability,readability,best_practices" \
    --severity_threshold "low" \
    --include_suggestions true \
    --output_format "actionable"
```

### 5.2 Address Code Quality Issues

**Issue**: Over-long descriptions, prompt template duplication, unused implementations

```bash
# Refactor for code quality improvements
exai refactor --target "code_quality_issues" \
    --refactor_type "quality_improvement" \
    --improvements "reduce_description_length,eliminate_duplication,remove_unused_code" \
    --maintain_functionality true
```

### 5.3 Add Observability

**Issue**: Missing observability, no metrics, logging, or health checks

```bash
# Add comprehensive observability
exai refactor --target "observability_system" \
    --refactor_type "add_observability" \
    --add_logging true \
    --add_metrics true \
    --add_health_checks true \
    --add_tracing true \
    --structured_logging true
```

## Phase 6: Testing and Validation

### 6.1 Generate Comprehensive Tests

```bash
# Generate tests for all fixed components
exai testgen --target "all_repaired_components" \
    --test_types "unit,integration,performance,security,boundary" \
    --coverage_threshold 90 \
    --include_edge_cases true \
    --include_error_scenarios true \
    --mock_external_dependencies true
```

### 6.2 Performance Testing

```bash
# Generate performance tests
exai testgen --target "performance_critical_components" \
    --test_types "performance,load,stress" \
    --include_benchmarks true \
    --test_large_inputs true \
    --memory_profiling true
```

### 6.3 Final Validation

```bash
# Run comprehensive precommit validation
exai precommit --scope "all_changes" \
    --include_tests true \
    --security_scan true \
    --performance_check true \
    --code_quality_check true \
    --documentation_check true
```

## Phase 7: Documentation and Finalization

### 7.1 Update Documentation

```bash
# Analyze documentation needs
exai analyze --target "documentation_requirements" \
    --analysis_type "documentation" \
    --focus_areas "api_changes,new_features,security_considerations" \
    --include_examples true

# Generate updated documentation
exai refactor --target "documentation" \
    --refactor_type "documentation_update" \
    --include_api_docs true \
    --include_security_docs true \
    --include_migration_guide true \
    --include_examples true
```

### 7.2 Final System Analysis

```bash
# Perform final comprehensive analysis
exai analyze --target "entire_repaired_system" \
    --analysis_type "comprehensive" \
    --focus_areas "functionality,security,performance,maintainability" \
    --depth "thorough" \
    --include_metrics true \
    --compare_baseline true
```

## Execution Guidelines

### Sequential Execution
1. **Do not skip phases** - each builds on the previous
2. **Validate after each phase** using precommit
3. **Document issues encountered** for future reference
4. **Test fixes immediately** after implementation

### Error Handling During Execution
1. **If exai commands fail**: Use debug workflow to investigate
2. **If consensus tool needed but broken**: Skip consensus steps until Phase 1.1 complete
3. **If self-analysis causes issues**: Use targeted scoping to avoid recursion
4. **If performance degrades**: Pause and investigate before continuing

### Quality Gates
- **After Phase 1**: All critical tools must be functional
- **After Phase 2**: Security audit must show no high/critical vulnerabilities
- **After Phase 3**: Performance tests must pass baseline requirements
- **After Phase 6**: Test coverage must be >90% for modified code
- **After Phase 7**: All documentation must be current and accurate

### Success Criteria
- ✅ Consensus tool fully functional
- ✅ All security vulnerabilities resolved
- ✅ Performance bottlenecks eliminated
- ✅ Code quality metrics improved
- ✅ Comprehensive test coverage achieved
- ✅ Documentation updated and accurate
- ✅ System passes all validation checks

## Troubleshooting Common Issues

### If Consensus Tool Still Fails After Phase 1.1
```bash
# Deep debug with manual investigation
exai debug --target "consensus_tool_deep_dive" \
    --investigation_depth "exhaustive" \
    --manual_investigation true \
    --trace_all_calls true
```

### If Self-Analysis Creates Recursion
```bash
# Use targeted analysis with exclusions
exai analyze --target "specific_component" \
    --exclude_paths "exai_tool_definitions" \
    --scope "limited" \
    --avoid_self_reference true
```

### If Performance Degrades During Fixes
```bash
# Performance regression analysis
exai analyze --target "performance_regression" \
    --analysis_type "performance" \
    --compare_baseline true \
    --identify_bottlenecks true
```

This systematic approach will comprehensively address all identified issues while maintaining system stability and functionality throughout the repair process.
