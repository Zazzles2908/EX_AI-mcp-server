# Routing Sequence (Detailed)

```mermaid
sequenceDiagram
  participant U as Client
  participant MCP as MCP Client
  participant S as Server (JSON-RPC)
  participant Tool as Tool (tools/*)
  participant R as RouterService (src/router/service.py)
  participant Reg as ModelProviderRegistry (src/providers/registry.py)
  participant Prov as Provider (GLM/Kimi/...)

  U->>MCP: Request
  MCP->>S: callTool
  S->>Tool: handle_call_tool
  Tool->>R: choose_model_with_hint(requested, hint)
  R->>Reg: get_provider_for_model(candidate)
  alt hint candidates available
    R-->>Tool: RouteDecision(reason: auto_hint_applied)
  else default preference
    R-->>Tool: RouteDecision(reason: auto_preferred)
  end
  Tool->>Prov: generate_content(...)
  Prov-->>Tool: content / usage
  Tool-->>S: result
  S-->>MCP: JSON-RPC result
```

Notes
- Hint is optional; when provided, RouterService logs whether hint influenced routing.
- Defaults prefer fast (GLM) then long-context (Kimi) if explicit model is not requested.

