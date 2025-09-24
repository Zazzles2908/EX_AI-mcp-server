# EX-AI MCP Server: System Cleanup & Architecture Improvement Plan

## Overview

Your EX-AI MCP server has grown into a complex system with 200+ environment variables, a 2600-line monolithic server file, and overlapping functionality. This plan provides a systematic approach to clean up and reorganize the system while maintaining functionality.

## Current System Analysis

### Complexity Metrics
- **server.py**: 2,600+ lines (should be <500 lines)
- **Environment Variables**: 200+ (should be <50 core variables)
- **Tool Registry**: 22+ tools with overlapping functionality
- **Provider Integrations**: Multiple wrapper layers causing confusion
- **Configuration Files**: Scattered across multiple locations

### Key Problems Identified

1. **Monolithic Architecture**: Everything in `server.py`
2. **Configuration Overload**: Too many environment variables
3. **Duplicate Functionality**: Multiple tools doing similar things
4. **Complex Provider Wrappers**: OpenAI-compatible layers hiding native capabilities
5. **Inconsistent Error Handling**: Different patterns across tools
6. **Missing AI Manager**: No intelligent routing as originally envisioned

## Phase 1: Core System Modularization

### 1.1 Break Down server.py

**Target Structure**:
```
src/server/
├── __init__.py
├── dispatcher.py          # Tool routing and execution (300 lines)
├── response_handler.py    # Response normalization (200 lines)
├── model_resolver.py      # Model selection logic (250 lines)
├── conversation_manager.py # Thread/continuation management (200 lines)
├── monitoring.py          # Logging and telemetry (150 lines)
└── mcp_protocol.py        # MCP protocol handling (200 lines)
```

**Implementation Steps**:

1. **Create dispatcher.py**:
```python
# src/server/dispatcher.py
from typing import Any, Dict, List, Callable
from mcp.types import TextContent
import logging

class ToolDispatcher:
    """Handles tool routing and execution with monitoring"""
    
    def __init__(self, tools: Dict[str, Any]):
        self.tools = tools
        self.logger = logging.getLogger(__name__)
    
    async def dispatch_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Main tool dispatch logic extracted from server.py"""
        # Move tool execution logic here
        pass
    
    def _validate_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """Validate tool arguments"""
        pass
    
    async def _execute_with_monitoring(self, tool_callable: Callable) -> Any:
        """Execute tool with timeout and progress monitoring"""
        pass
```

2. **Create response_handler.py**:
```python
# src/server/response_handler.py
from typing import List, Any
from mcp.types import TextContent
import json

class ResponseHandler:
    """Standardizes and validates tool responses"""
    
    def normalize_response(self, result: Any, tool_name: str) -> List[TextContent]:
        """Convert any tool response to standard MCP format"""
        pass
    
    def validate_response_content(self, result: List[TextContent], tool_name: str) -> bool:
        """Ensure response contains actual content"""
        pass
    
    def add_metadata(self, result: List[TextContent], metadata: Dict[str, Any]) -> List[TextContent]:
        """Add progress and debugging metadata"""
        pass
```

3. **Create model_resolver.py**:
```python
# src/server/model_resolver.py
from typing import Dict, Any, Optional
from src.providers.registry import ModelProviderRegistry

class ModelResolver:
    """Handles intelligent model selection and routing"""
    
    def resolve_model(self, requested_model: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Resolve 'auto' and apply routing logic"""
        pass
    
    def get_optimal_provider(self, task_type: str, content_hints: Dict[str, Any]) -> str:
        """Choose between Moonshot/Z.ai based on task requirements"""
        pass
```

### 1.2 Implement AI Manager Architecture

**File**: `src/managers/ai_manager.py`

```python
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

class TaskType(Enum):
    WEB_RESEARCH = "web_research"
    FILE_ANALYSIS = "file_analysis"
    CODE_REVIEW = "code_review"
    LONG_CONTEXT = "long_context"
    FAST_RESPONSE = "fast_response"

@dataclass
class RoutingDecision:
    provider: str  # "moonshot" | "zhipu"
    model: str
    tools: List[str]
    reasoning: str

class AIManager:
    """GLM-4.5-flash powered intelligent request router"""
    
    def __init__(self):
        self.router_model = "glm-4.5-flash"  # Fast decision making
    
    async def analyze_request(self, prompt: str, files: List[str] = None) -> TaskType:
        """Analyze user request to determine task type"""
        # Use GLM-4.5-flash to classify the request
        analysis_prompt = f"""
        Analyze this user request and classify the task type:
        
        Request: {prompt}
        Files provided: {len(files or [])}
        
        Classify as one of:
        - web_research: Needs current information, news, or web data
        - file_analysis: Analyzing uploaded files or documents
        - code_review: Code analysis, debugging, or development
        - long_context: Complex reasoning requiring large context window
        - fast_response: Simple questions needing quick answers
        
        Respond with just the classification.
        """
        
        # Call GLM-4.5-flash for classification
        # Implementation here...
        pass
    
    async def route_request(self, task_type: TaskType, context: Dict[str, Any]) -> RoutingDecision:
        """Determine optimal provider and tool chain"""
        
        if task_type == TaskType.WEB_RESEARCH:
            return RoutingDecision(
                provider="zhipu",  # Z.ai has better web browsing
                model="glm-4.5",
                tools=["glm_web_search", "glm_multi_file_chat"],
                reasoning="Web research requires Z.ai's native web capabilities"
            )
        
        elif task_type == TaskType.LONG_CONTEXT:
            return RoutingDecision(
                provider="moonshot",  # Moonshot excels at long context
                model="kimi-k2-0905-preview",
                tools=["kimi_upload_and_extract", "kimi_multi_file_chat"],
                reasoning="Long context analysis benefits from Moonshot's context window"
            )
        
        elif task_type == TaskType.FAST_RESPONSE:
            return RoutingDecision(
                provider="zhipu",
                model="glm-4.5-flash",
                tools=["chat"],
                reasoning="Fast response using GLM flash model"
            )
        
        # Add other routing logic...
        
    async def enhance_prompt(self, original_prompt: str, routing: RoutingDecision) -> str:
        """Enhance user prompt with context and routing hints"""
        enhancement_prompt = f"""
        Original request: {original_prompt}
        
        Routing decision: Using {routing.provider} with {routing.model}
        Reasoning: {routing.reasoning}
        
        Enhance this prompt to work optimally with the selected provider and model.
        Add any necessary context or formatting for best results.
        """
        
        # Use GLM-4.5-flash to enhance the prompt
        # Implementation here...
        pass
```

## Phase 2: Configuration Simplification

### 2.1 Core Configuration Reduction

**Target**: Reduce from 200+ to 50 essential variables

**New Configuration Structure**:

```bash
# === CORE PROVIDER KEYS (Required) ===
KIMI_API_KEY=your_moonshot_key
GLM_API_KEY=your_zhipu_key

# === MODEL DEFAULTS ===
DEFAULT_MODEL=auto                    # Let AI manager decide
KIMI_DEFAULT_MODEL=kimi-k2-0905-preview
GLM_DEFAULT_MODEL=glm-4.5-flash
GLM_QUALITY_MODEL=glm-4.5
KIMI_QUALITY_MODEL=kimi-k2-0905-preview

# === CORE FEATURES ===
ENABLE_AI_MANAGER=true               # Use intelligent routing
ENABLE_WEB_SEARCH=true               # Enable web capabilities
ENABLE_FILE_UPLOAD=true              # Enable file processing
ENABLE_FALLBACK=true                 # Enable provider fallback

# === TIMEOUTS (Seconds) ===
TOOL_TIMEOUT=120                     # Max tool execution time
PROVIDER_TIMEOUT=60                  # Max provider API call time
UPLOAD_TIMEOUT=180                   # File upload timeout

# === SERVER CONFIG ===
MCP_SERVER_NAME=exai
EXAI_WS_HOST=127.0.0.1
EXAI_WS_PORT=8765
LOG_LEVEL=INFO

# === OPTIONAL PROVIDERS ===
OPENROUTER_API_KEY=                  # Optional
CUSTOM_API_URL=                      # Optional local models

# === ADVANCED (Optional) ===
MAX_FILE_SIZE_MB=100                 # File upload limit
MAX_CONTEXT_TOKENS=128000            # Context window limit
ENABLE_CACHING=true                  # Response caching
CACHE_TTL_HOURS=24                   # Cache duration
```

### 2.2 Configuration Migration Script

**File**: `scripts/migrate_config.py`

```python
#!/usr/bin/env python3
"""
Migrate from complex .env to simplified configuration
"""

import os
from pathlib import Path

# Mapping from old complex config to new simplified config
CONFIG_MIGRATION = {
    # Core providers
    "KIMI_API_KEY": "KIMI_API_KEY",
    "GLM_API_KEY": "GLM_API_KEY",
    
    # Model defaults
    "DEFAULT_MODEL": "DEFAULT_MODEL",
    "KIMI_DEFAULT_MODEL": "KIMI_DEFAULT_MODEL", 
    "GLM_FLASH_MODEL": "GLM_DEFAULT_MODEL",
    
    # Features
    "EX_WEBSEARCH_ENABLED": "ENABLE_WEB_SEARCH",
    "ENABLE_CONSENSUS_AUTOMODE": None,  # Remove complex features
    
    # Timeouts
    "EX_TOOL_TIMEOUT_SECONDS": "TOOL_TIMEOUT",
    "KIMI_MF_CHAT_TIMEOUT_SECS": "PROVIDER_TIMEOUT",
    
    # Server
    "MCP_SERVER_NAME": "MCP_SERVER_NAME",
    "EXAI_WS_HOST": "EXAI_WS_HOST",
    "EXAI_WS_PORT": "EXAI_WS_PORT",
}

def migrate_config():
    """Migrate old .env to new simplified format"""
    old_env = Path(".env")
    new_env = Path(".env.new")
    
    if not old_env.exists():
        print("No .env file found")
        return
    
    # Read old config
    old_config = {}
    with open(old_env) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                old_config[key] = value
    
    # Generate new config
    new_config = []
    new_config.append("# === EX-AI MCP Server - Simplified Configuration ===")
    new_config.append("")
    
    # Core providers
    new_config.append("# === CORE PROVIDER KEYS (Required) ===")
    new_config.append(f"KIMI_API_KEY={old_config.get('KIMI_API_KEY', '')}")
    new_config.append(f"GLM_API_KEY={old_config.get('GLM_API_KEY', '')}")
    new_config.append("")
    
    # Add other sections...
    
    # Write new config
    with open(new_env, 'w') as f:
        f.write('\n'.join(new_config))
    
    print(f"New simplified config written to {new_env}")
    print("Review the new config and replace .env when ready")

if __name__ == "__main__":
    migrate_config()
```

## Phase 3: Tool Consolidation

### 3.1 Current Tool Analysis

**Redundant Tools to Consolidate**:
- `chat` + `kimi_chat_with_tools` → `smart_chat`
- `analyze` + `thinkdeep` → `deep_analyze`
- `kimi_upload_and_extract` + `kimi_multi_file_chat` → `file_chat`
- Multiple consensus tools → `consensus`

### 3.2 New Simplified Tool Set

**Target: 12 Core Tools**

```python
# New simplified tool registry
CORE_TOOLS = {
    # === CORE INTERACTION ===
    "chat": "Smart chat with AI manager routing",
    "file_chat": "Upload files and chat about them",
    "web_search": "Search web and analyze results",
    
    # === CODE & ANALYSIS ===
    "analyze": "Deep analysis with multi-step reasoning",
    "code_review": "Review code for issues and improvements", 
    "debug": "Debug code issues and suggest fixes",
    "refactor": "Refactor and improve code structure",
    
    # === UTILITIES ===
    "consensus": "Get multiple AI perspectives",
    "planner": "Create project plans and roadmaps",
    "testgen": "Generate comprehensive tests",
    
    # === SYSTEM ===
    "status": "Check system health and capabilities",
    "activity": "View recent activity and logs",
}
```

### 3.3 Smart Tool Implementation

**File**: `tools/smart/smart_chat.py`

```python
from typing import Dict, Any, List
from mcp.types import TextContent
from tools.shared.base_tool import BaseTool
from src.managers.ai_manager import AIManager

class SmartChatTool(BaseTool):
    """Intelligent chat that routes to optimal provider"""
    
    def __init__(self):
        self.ai_manager = AIManager()
    
    def get_name(self) -> str:
        return "chat"
    
    def get_description(self) -> str:
        return "Smart chat with automatic provider routing based on request type"
    
    async def execute(self, arguments: Dict[str, Any]) -> List[TextContent]:
        prompt = arguments.get("prompt", "")
        files = arguments.get("files", [])
        
        # Let AI manager analyze and route the request
        task_type = await self.ai_manager.analyze_request(prompt, files)
        routing = await self.ai_manager.route_request(task_type, arguments)
        enhanced_prompt = await self.ai_manager.enhance_prompt(prompt, routing)
        
        # Execute using the routed provider
        if routing.provider == "moonshot":
            return await self._execute_moonshot(enhanced_prompt, routing, arguments)
        elif routing.provider == "zhipu":
            return await self._execute_zhipu(enhanced_prompt, routing, arguments)
        else:
            # Fallback to default
            return await self._execute_default(prompt, arguments)
    
    async def _execute_moonshot(self, prompt: str, routing, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute using Moonshot/Kimi provider"""
        # Implementation here...
        pass
    
    async def _execute_zhipu(self, prompt: str, routing, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute using ZhipuAI/GLM provider"""
        # Implementation here...
        pass
```

## Phase 4: Native Provider Integration

### 4.1 Replace OpenAI-Compatible Wrappers

**Current Problem**: Using OpenAI-compatible clients loses native capabilities

**Solution**: Implement native SDK integrations

**File**: `src/providers/zhipu_native.py`

```python
import zhipuai
from typing import Dict, Any, List, Optional

class ZhipuNativeProvider:
    """Native ZhipuAI integration with full capabilities"""
    
    def __init__(self, api_key: str):
        self.client = zhipuai.ZhipuAI(api_key=api_key)
    
    async def chat_with_web_search(self, messages: List[Dict], model: str = "glm-4.5") -> Dict[str, Any]:
        """Use native web search capabilities"""
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[{
                "type": "web_search",
                "web_search": {
                    "enable": True,
                    "search_query": "auto"  # Let model determine search terms
                }
            }]
        )
        return self._format_response(response)
    
    async def upload_and_analyze_file(self, file_path: str, prompt: str) -> Dict[str, Any]:
        """Native file upload and analysis"""
        # Use ZhipuAI's native file handling
        file_object = self.client.files.create(
            file=open(file_path, "rb"),
            purpose="retrieval"
        )
        
        response = self.client.chat.completions.create(
            model="glm-4.5",
            messages=[
                {"role": "user", "content": prompt, "attachments": [{"file_id": file_object.id}]}
            ]
        )
        return self._format_response(response)
    
    def _format_response(self, response) -> Dict[str, Any]:
        """Format response to standard envelope"""
        try:
            content = response.choices[0].message.content
            return {
                "status": "success",
                "content": content,
                "provider": "ZHIPU_NATIVE",
                "model": response.model,
                "usage": response.usage.dict() if response.usage else None
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "provider": "ZHIPU_NATIVE"
            }
```

### 4.2 Enhanced Moonshot Integration

**File**: `src/providers/moonshot_native.py`

```python
from openai import OpenAI
from typing import Dict, Any, List, Optional

class MoonshotNativeProvider:
    """Enhanced Moonshot integration with file-based QA patterns"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.moonshot.ai/v1"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
    
    async def file_based_qa(self, file_paths: List[str], question: str, model: str = "kimi-k2-0905-preview") -> Dict[str, Any]:
        """Use Moonshot's recommended file-based QA pattern"""
        
        # Upload files and get file IDs
        file_ids = []
        for file_path in file_paths:
            with open(file_path, 'rb') as f:
                file_obj = self.client.files.create(file=f, purpose="file-extract")
                file_ids.append(file_obj.id)
        
        # Use file attachment pattern instead of content injection
        messages = [{
            "role": "user",
            "content": question,
            "attachments": [
                {"file_id": fid, "tools": [{"type": "file_search"}]} 
                for fid in file_ids
            ]
        }]
        
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3
        )
        
        return self._format_response(response, {"files_processed": len(file_paths)})
    
    async def long_context_chat(self, messages: List[Dict], model: str = "kimi-k2-0905-preview") -> Dict[str, Any]:
        """Optimized for long context conversations"""
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.6,
            # Use context caching for long conversations
            extra_headers={"Msh-Context-Cache": "auto"}
        )
        return self._format_response(response)
    
    def _format_response(self, response, metadata: Dict = None) -> Dict[str, Any]:
        """Format response to standard envelope"""
        try:
            content = response.choices[0].message.content
            return {
                "status": "success",
                "content": content,
                "provider": "MOONSHOT_NATIVE",
                "model": response.model,
                "usage": response.usage.dict() if response.usage else None,
                "metadata": metadata or {}
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "provider": "MOONSHOT_NATIVE"
            }
```

## Implementation Timeline

### Week 1: Core Fixes
- ✅ Apply immediate fixes from previous document
- ✅ Create basic modular structure
- ✅ Implement AI manager foundation

### Week 2: Configuration Cleanup
- ✅ Create simplified configuration
- ✅ Build migration script
- ✅ Test with reduced config set

### Week 3: Tool Consolidation
- ✅ Implement smart tools
- ✅ Consolidate redundant functionality
- ✅ Update tool registry

### Week 4: Native Providers
- ✅ Implement native ZhipuAI integration
- ✅ Enhance Moonshot integration
- ✅ Test end-to-end functionality

## Success Metrics

### Code Quality
- **server.py**: Reduced from 2600 to <500 lines
- **Configuration**: Reduced from 200+ to 50 variables
- **Tools**: Consolidated from 22+ to 12 core tools

### Functionality
- ✅ AI Manager intelligently routes requests
- ✅ Native provider capabilities fully utilized
- ✅ Response content consistently delivered
- ✅ Fallback system works reliably

### Maintainability
- ✅ Clear separation of concerns
- ✅ Standardized error handling
- ✅ Comprehensive logging
- ✅ Easy to add new providers/tools

This cleanup plan transforms your complex system into a clean, maintainable architecture while preserving all functionality and adding the intelligent AI manager you originally envisioned.
