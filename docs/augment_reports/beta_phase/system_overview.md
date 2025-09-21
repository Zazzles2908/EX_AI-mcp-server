# EXAI-WS MCP — System Overview (Beta Phase)

Status: Initial snapshot — aligns with current .env and provider wiring. Will update after first backend MCP run.

## Mermaid — High-level Call Flow

```mermaid
sequenceDiagram
    participant UI as Client (VS Code / CLI)
    participant WS as EXAI-WS Daemon (WebSocket)
    participant REG as ToolRegistry (tools/registry.py)
    participant TOOL as Tool (e.g., kimi_upload_and_extract)
    participant PROV as Provider (Kimi/GLM wrapper)
    participant API as OpenAI-compatible API (Kimi/GLM)

    UI->>WS: hello + list_tools (JSON-RPC over WS)
    UI->>WS: call_tool{name, arguments, request_id}
    WS->>REG: resolve tool by name
    REG->>TOOL: instantiate/execute (async execute->to_thread for I/O)
    TOOL->>PROV: provider call (upload/chat/websearch)
    PROV->>API: OpenAI-compatible request (base_url per provider)
    API-->>PROV: response (stream/non-stream)
    PROV-->>TOOL: normalized result {provider, model, content, usage, raw}
    TOOL-->>WS: outputs[] (TextContent JSON)
    WS-->>UI: call_tool_res{request_id, outputs}
```

## Operational Notes (current config)
- Default manager: glm-4.5-flash (DEFAULT_MODEL)
- Kimi base URL: https://api.moonshot.ai/v1 (KIMI_API_URL)
- WS ping interval/timeout: 45s / 120s; open_timeout: 60s; call_timeout: 240s
- Tool timeout: TOOL_EXEC_TIMEOUT_SEC=90 (daemon-level); KIMI chat tool web timeout=300s
- Compatibility: EXAI_WS_COMPAT_TEXT=true (monitor for UI-mapping side effects)

## What gets logged during backend runs
- WS frames: hello, list_tools, call_tool, call_tool_res (raw JSON)
- Per-call: tool name, arguments, request_id, provider/model selected, timing, preview text
- Artifacts: timestamped run folders with raw outputs + markdown summary

## Next updates
- After the first run, attach a route_diagnostics table (tool -> model -> provider -> script entrypoint)
- Add error taxonomy if cancellations occur (timeout vs. provider 4xx/5xx vs. client-side)



## Mermaid — Manager/Router Layer

```mermaid
flowchart TD
  A[Client request] --> B{Manager/Router}
  B -->|Classify: content-only| C[chat]
  B -->|Classify: file ops| D[kimi_upload_and_extract]
  B -->|Classify: multi-file review| E[kimi_multi_file_chat]
  B -->|Classify: deep analysis| F[analyze/thinkdeep]
  B -->|Classify: diagnostics| G[activity/health/provider_capabilities]

  C -->|route| C1{Model pick}
  C1 -->|websearch true| C2[GLM 4.5 / 4.5-air]
  C1 -->|no websearch| C3[Kimi K2 / GLM flash]

  D --> K1[Kimi Files API]
  E --> K2[Kimi Chat w/ uploaded files]
  F --> M1[Manager delegates to tool-specific flow]
  G --> S1[System tools]
```

## Mermaid — Tool Function Breakdown

```mermaid
classDiagram
  class chat {
    +prompt: str
    +model?: str
    +use_websearch?: bool
    +returns: TextContent[]
  }
  class kimi_upload_and_extract {
    +files: str[]
    +purpose: "file-extract"
    +returns: file_ids[], extracted_text
  }
  class kimi_multi_file_chat {
    +files: str[]
    +prompt: str
    +model?: str
    +temperature?: float
    +returns: TextContent[]
  }
  class analyze {
    +step: str
    +step_number: int
    +findings: str
    +returns: summary/detail/actionable
  }
  class activity {
    +lines?: int
    +filter?: str
    +returns: log tail
  }

  chat --> "may call" websearch
  kimi_upload_and_extract --> "uses" Kimi Files API
  kimi_multi_file_chat --> "uses" Kimi Chat + Files
  analyze --> "manager-driven orchestration"
```
