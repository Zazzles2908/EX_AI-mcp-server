# Duplicate Domains (Visual Map)

```mermaid
graph TD
  subgraph Canonical (src/*)
    SRC_PROV[src/providers/*]
    SRC_ROUT[src/router/*]
    SRC_TOOLS[tools/*]
  end

  subgraph Legacy Shims (temporary)
    LEG_PROV[providers/* (shim)]
    ROUT_SHIM[routing/* (shim)]
  end

  SRC_TOOLS --> SRC_ROUT
  SRC_ROUT --> SRC_PROV

  LEG_PROV -.redirects.-> SRC_PROV
  ROUT_SHIM -.re-exports.-> SRC_ROUT

  style LEG_PROV fill:#fff3cd,stroke:#f0ad4e
  style ROUT_SHIM fill:#fff3cd,stroke:#f0ad4e
  style SRC_PROV fill:#d1e7dd,stroke:#198754
  style SRC_ROUT fill:#d1e7dd,stroke:#198754
```

Notes
- src/* is the source of truth; top-level providers/ and routing/ exist only as shims during migration.
- After the green window, we remove legacy trees and shims.

