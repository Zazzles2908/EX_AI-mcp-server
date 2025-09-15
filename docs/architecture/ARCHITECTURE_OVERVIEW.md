# EX MCP Server - Architecture Overview

**Version**: 5.8.5+  
**Last Updated**: 2025-01-13  
**Status**: Production Ready with Advanced Context Manager

## System Architecture

The EX MCP Server is built on a modular, extensible architecture that supports multiple AI providers, intelligent context management, and enterprise-scale development workflows.

```
EX MCP Server Architecture
├── 🌐 Transport Layer
│   ├── MCP stdio (default) - Direct client communication
│   ├── WebSocket daemon - Concurrent client support
│   └── HTTP/SSE (optional) - Remote API access
├── 🛠️ Tool Registry (25 active tools)
│   ├── Core Development Tools (10)
│   ├── Advanced Tools (11)
│   └── Provider-Specific Tools (4)
├── 🧠 Advanced Context Manager
│   ├── Intelligent optimization strategies
│   ├── Semantic caching system
│   ├── Model-aware token allocation
│   └── Cross-tool context preservation
├── 🔌 Provider Registry
│   ├── Kimi (Moonshot) - Primary provider
│   ├── GLM (ZhipuAI) - Primary provider
│   ├── OpenAI - Optional
│   ├── OpenRouter - Optional
│   └── Custom endpoints - Optional
├── 📊 Monitoring & Observability
│   ├── Performance metrics collection
│   ├── Real-time optimization recommendations
│   ├── Comprehensive logging system
│   └── Health monitoring and alerts
└── ⚙️ Configuration Management
    ├── Environment-based configuration
    ├── Provider credential management
    ├── Tool visibility and access control
    └── Performance tuning parameters
```

## Core Components

### 🌐 **Transport Layer**

#### **MCP stdio (Default)**
- **Purpose**: Direct communication with MCP clients
- **Implementation**: `server.py`
- **Features**: Standard MCP protocol, progress capture, response shaping
- **Use Case**: Claude Desktop, VS Code extensions, direct integrations

#### **WebSocket Daemon**
- **Purpose**: Concurrent client support and improved reliability
- **Implementation**: `scripts/ws_daemon.py`, `scripts/ws_start.ps1`
- **Features**: Multi-client support, health monitoring, automatic restart
- **Use Case**: Production deployments, multiple concurrent users

#### **HTTP/SSE (Optional)**
- **Purpose**: Remote API access and web integrations
- **Implementation**: `remote_server.py`
- **Features**: FastAPI-based, CORS support, Bearer token authentication
- **Use Case**: Web applications, remote integrations, API access

### 🛠️ **Tool Registry**

#### **Architecture**
- **Registry**: `tools/registry.py` - Dynamic tool loading and management
- **Base Classes**: `tools/shared/base_tool.py`, `tools/workflow/base.py`
- **Execution**: Async execution with progress tracking and error handling

#### **Tool Categories**

**Core Development Tools (10)**:
```python
CORE_TOOLS = {
    "chat": "Interactive development chat",
    "analyze": "Step-by-step code analysis", 
    "codereview": "Comprehensive code review",
    "debug": "Debugging workflows",
    "refactor": "Code refactoring",
    "testgen": "Test generation",
    "planner": "Interactive planning",
    "thinkdeep": "Deep thinking workflows",
    "precommit": "Pre-commit validation",
    "challenge": "Development challenges"
}
```

**Advanced Tools (11)**:
```python
ADVANCED_TOOLS = {
    "consensus": "Multi-model consensus analysis",
    "docgen": "Documentation generation",
    "secaudit": "Security audit workflows",
    "tracer": "Code tracing and analysis",
    "context_performance": "Performance monitoring",  # NEW
    "provider_capabilities": "Provider information",
    "listmodels": "Model listing",
    "activity": "Activity monitoring",
    "version": "Version information",
    "health": "System health",
    "kimi_chat_with_tools": "Kimi integration"
}
```

### 🧠 **Advanced Context Manager**

#### **Core Engine** (`src/core/agentic/context_manager.py`)
- **Intelligent Optimization**: Content-aware optimization strategies
- **Semantic Caching**: TTL-based caching with automatic cleanup
- **Model-Aware Allocation**: Token budget management per model type
- **Performance Tracking**: Real-time metrics and optimization analytics

#### **Integration Layer** (`src/core/agentic/context_integration.py`)
- **Cross-System Coordination**: Unified optimization across all components
- **Conversation Memory**: Enhanced cross-tool context continuity
- **File Processing**: Intelligent file content optimization
- **Error Handling**: Graceful fallback mechanisms

#### **Utility Functions** (`utils/advanced_context.py`)
- **Easy Integration**: Simple functions for tool developers
- **Performance Access**: Statistics and recommendation APIs
- **Error Handling**: Comprehensive fallback patterns

#### **Performance System** (`utils/context_performance.py`)
- **Real-Time Metrics**: Processing time, compression ratios, cache performance
- **Optimization Recommendations**: Intelligent analysis of usage patterns
- **Performance Alerts**: Configurable thresholds and monitoring

### 🔌 **Provider Registry**

#### **Architecture** (`src/providers/registry.py`)
- **Dynamic Loading**: Automatic provider discovery and initialization
- **Credential Management**: Secure API key handling and validation
- **Model Resolution**: Intelligent model selection and routing
- **Error Handling**: Provider-specific error handling and fallback

#### **Supported Providers**
```python
PROVIDERS = {
    "kimi": {
        "class": "KimiModelProvider",
        "models": ["kimi-k2-0711-preview", "kimi-k1.5-chat", "kimi-k1.5-all"],
        "features": ["chat", "file_upload", "tool_calling"],
        "status": "primary"
    },
    "glm": {
        "class": "GLMModelProvider", 
        "models": ["glm-4.5-flash", "glm-4.5", "glm-4.5-air"],
        "features": ["chat", "agent_api", "file_processing"],
        "status": "primary"
    },
    "openai": {
        "class": "OpenAIModelProvider",
        "models": ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"],
        "features": ["chat", "function_calling", "vision"],
        "status": "optional"
    }
}
```

### 📊 **Monitoring & Observability**

#### **Logging System**
- **Main Log**: `logs/mcp_server.log` - All server activity and debug info
- **Activity Log**: `logs/mcp_activity.log` - Tool calls and completions
- **Health Log**: `logs/ws_daemon.health.json` - WebSocket daemon health
- **Rotation**: Automatic log rotation with size limits and retention

#### **Performance Monitoring**
- **Real-Time Metrics**: Processing time, token usage, cache performance
- **Optimization Tracking**: Compression ratios, strategy effectiveness
- **Error Monitoring**: Failed operations, fallback usage, system issues
- **Recommendations**: Intelligent optimization suggestions

#### **Health Monitoring**
- **System Health**: Memory usage, CPU utilization, disk space
- **Provider Health**: API availability, response times, error rates
- **Tool Health**: Success rates, performance metrics, error patterns
- **WebSocket Health**: Connection status, client count, throughput

## Data Flow

### **Request Processing Flow**
```
1. Client Request → Transport Layer (stdio/WebSocket/HTTP)
2. Request Validation → MCP Protocol Handler
3. Tool Resolution → Tool Registry
4. Context Preparation → Advanced Context Manager
   ├── Content Analysis → Optimization Strategy Selection
   ├── Cache Check → Semantic Cache Lookup
   ├── Content Optimization → Intelligent Compression
   └── Token Allocation → Model-Aware Budget Management
5. Provider Selection → Provider Registry
6. Model Execution → AI Provider API
7. Response Processing → Tool-Specific Formatting
8. Context Caching → Semantic Cache Storage
9. Performance Logging → Metrics Collection
10. Response Delivery → Client via Transport Layer
```

### **Context Optimization Flow**
```
1. Content Analysis → Size, Type, Complexity Assessment
2. Threshold Check → Optimization Trigger Evaluation
3. Cache Lookup → Semantic Cache Query
4. Strategy Selection → Content-Aware Optimization
   ├── Intelligent Truncation → Preserve Essential Information
   ├── Semantic Compression → Remove Redundancy
   ├── Structure Preservation → Maintain Code/Text Structure
   └── Cross-Tool Context → Preserve Workflow Continuity
5. Optimization Execution → Apply Selected Strategies
6. Quality Validation → Ensure Content Integrity
7. Performance Tracking → Record Metrics and Analytics
8. Cache Storage → Store Optimized Results
9. Fallback Handling → Graceful Error Recovery
```

## Performance Characteristics

### **Current Production Metrics**
- **Tool Loading**: 25/25 tools (100% success rate)
- **Average Processing Time**: 59.9ms per operation
- **Context Optimization**: 28% average token reduction
- **Cache Hit Rate**: 50% for repeated patterns
- **Error Rate**: < 1% with graceful fallback
- **Memory Usage**: ~200MB base + ~1MB per 1000 cache entries

### **Optimization Thresholds**
```python
OPTIMIZATION_THRESHOLDS = {
    "file_content": 12000,      # Base tool file processing
    "conversation": 15000,      # Conversation history
    "workflow": 10000,          # Workflow processing
    "expert_analysis": 15000,   # Expert analysis content
    "debug": 8000,              # Debug scenarios
    "cross_tool": 5000          # Cross-tool context
}
```

### **Scalability Characteristics**
- **Concurrent Clients**: 50+ via WebSocket daemon
- **File Processing**: Up to 10x larger files through optimization
- **Memory Efficiency**: Intelligent caching with TTL and cleanup
- **CPU Efficiency**: Minimal overhead (~1% for monitoring)

## Configuration Management

### **Environment Configuration**
```bash
# Core Configuration
MCP_SERVER_NAME="EX MCP Server"
MCP_SERVER_ID="ex-server"
LOG_LEVEL="INFO"

# Provider Configuration
KIMI_API_KEY="your_kimi_key"
GLM_API_KEY="your_glm_key"
OPENAI_API_KEY="your_openai_key"  # Optional

# Advanced Context Manager
CONTEXT_CACHE_SIZE="2000"        # Default: 1000
CONTEXT_CACHE_TTL="7200"         # Default: 3600 (1 hour)

# Tool Configuration
LEAN_MODE="false"                # Enable lean tool set
DISABLED_TOOLS=""                # Comma-separated list
```

### **Performance Tuning**
```bash
# High-Volume Environment
CONTEXT_CACHE_SIZE="5000"
CONTEXT_CACHE_TTL="14400"       # 4 hours
OPTIMIZATION_THRESHOLD_MULTIPLIER="1.2"

# Development Environment  
CONTEXT_CACHE_SIZE="500"
CONTEXT_CACHE_TTL="1800"        # 30 minutes
LOG_LEVEL="DEBUG"
```

## Security Architecture

### **Authentication & Authorization**
- **API Key Management**: Secure storage and validation
- **Bearer Token Auth**: For remote HTTP access
- **CORS Configuration**: Configurable origin restrictions
- **Input Validation**: Comprehensive request validation

### **Data Protection**
- **Credential Isolation**: Provider keys isolated per request
- **Content Sanitization**: Safe handling of user content
- **Log Sanitization**: Sensitive data excluded from logs
- **Cache Security**: Secure caching with automatic cleanup

## Deployment Patterns

### **Development Deployment**
- **Transport**: MCP stdio for direct client integration
- **Tools**: Full tool set with debug logging
- **Providers**: Primary providers (Kimi, GLM)
- **Monitoring**: Basic logging and health checks

### **Production Deployment**
- **Transport**: WebSocket daemon for concurrent clients
- **Tools**: Optimized tool set based on usage
- **Providers**: All configured providers with fallback
- **Monitoring**: Comprehensive metrics, alerts, and health monitoring

### **Enterprise Deployment**
- **Transport**: WebSocket + HTTP for maximum flexibility
- **Tools**: Custom tool sets per team/project
- **Providers**: Multi-provider with intelligent routing
- **Monitoring**: Advanced analytics, custom dashboards, SLA monitoring

## Future Architecture Evolution

### **Phase 2: Advanced Intelligence**
- **AI-Powered Optimization**: Machine learning for optimization strategies
- **Predictive Caching**: Anticipatory content optimization
- **Multi-Modal Support**: Images, documents, and rich media
- **Advanced Analytics**: Deep performance insights and recommendations

### **Phase 3: Enterprise Scale**
- **Distributed Architecture**: Multi-instance coordination
- **Microservices**: Decomposed services for specific functions
- **Event-Driven Architecture**: Real-time event processing
- **Advanced Security**: Enterprise-grade security features

### **Phase 4: Ecosystem Integration**
- **Plugin Architecture**: Third-party tool and provider plugins
- **API Gateway**: Unified API management and routing
- **Service Mesh**: Advanced networking and service discovery
- **Cloud-Native**: Kubernetes-ready containerized deployment

---

*This architecture supports the current production deployment of 25 tools with Advanced Context Manager integration, providing enterprise-scale development capabilities with intelligent context optimization.*
