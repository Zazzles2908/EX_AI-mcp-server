# System Flow Diagram (Augment)

Status: Visual quick reference

```mermaid
graph TD
  subgraph ClientSide
    U[User / IDE / CLI]
    MCPClient[MCP Client]
  end

  U --> MCPClient
  MCPClient -->|JSON-RPC stdio+WS| Server[server.py]

  Server --> LT[list_tools]
  Server --> CT[handle_call_tool]
  CT --> Tool[tools/*]

  Tool --> Router[RouterService (src/router/service.py)]
  Router --> Conf[configure_providers()]
  Conf --> Registry[ModelProviderRegistry (src/providers/registry.py)]

  Registry -->|selects| Provider[Provider impl]
  Provider -->|SDK or HTTP| External[GLM / Kimi / OpenAI-Compatible APIs]

  Tool -. heuristic .-> ATR[IntelligentTaskRouter (src/core/agentic/task_router.py)]
  ATR -. suggest .-> Router

  Server --> Logs[.logs/*]
```

Notes
- src/providers is canonical for providers; top-level providers/ is a temporary shim
- Tools live under tools/ and call into RouterService when models are needed
- Agentic router is optional and should not conflict with RouterService decisions

