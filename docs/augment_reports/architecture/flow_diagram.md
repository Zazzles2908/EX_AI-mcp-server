# System Flow Diagram (Augment)

Status: Visual quick reference

```mermaid
graph TD
  U[Client] --> C[MCP Client]
  C --> S[Server]
  S --> LT[list_tools]
  S --> CT[handle_call_tool]
  CT --> T[tools]
  T --> R[RouterService]
  R --> REG[ModelProviderRegistry]
  REG --> P[Provider]
  P --> X[Upstream APIs]
  T -.-> AR[IntelligentTaskRouter]
  AR -.-> R
  S --> L[logs]
```

Notes
- src/providers is canonical for providers; top-level providers/ is a temporary shim
- Tools live under tools/ and call into RouterService when models are needed
- Agentic router is optional and should not conflict with RouterService decisions

