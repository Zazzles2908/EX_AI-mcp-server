# Duplicate Domains (Visual Map)

```mermaid
graph TD
  SRC_PROV["src/providers/*"]
  SRC_ROUT["src/router/*"]
  TOOLS["tools/*"]
  LEG_PROV["providers/* (shim)"]
  LEG_ROUT["routing/* (shim)"]

  TOOLS --> SRC_ROUT
  SRC_ROUT --> SRC_PROV
  LEG_PROV --> SRC_PROV
  LEG_ROUT --> SRC_ROUT
```

Notes
- src/* is the source of truth; top-level providers/ and routing/ exist only as shims during migration.
- After the green window, we remove legacy trees and shims.

