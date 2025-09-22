# Back-compat shim: forwards to canonical subfolder
if __name__ == "__main__":
    import pathlib, runpy, sys
    target = pathlib.Path(__file__).parent / "diagnostics" / "router_service_diagnostics_smoke.py"
    try:
        runpy.run_path(str(target), run_name="__main__")
    except SystemExit as e:
        raise
    except Exception as e:
        print(f"Shim failed to run target {target}: {e}")
        sys.exit(1)
    sys.exit(0)


#!/usr/bin/env python
"""
RouterService diagnostics smoke (provider-safe)
- Disables preflight chat probes
- Enables diagnostics logging
- Exercises choose_model() and choose_model_with_hint() across common scenarios
- Emits compact JSON lines to stdout and exits 0 on success
"""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Dict, List

# Provider-safe env guards
os.environ.setdefault("ROUTER_PREFLIGHT_CHAT", "false")
os.environ.setdefault("ROUTER_DIAGNOSTICS_ENABLED", "true")
os.environ.setdefault("ROUTER_LOG_LEVEL", "INFO")

# Prefer fast/long defaults that exist in this fork
os.environ.setdefault("FAST_MODEL_DEFAULT", "glm-4.5-flash")
os.environ.setdefault("LONG_MODEL_DEFAULT", "kimi-k2-0711-preview")

# Minimal logging setup (JSON lines on 'router' logger are produced inside RouterService)
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Ensure repository root on sys.path for 'src' imports
try:
    import pathlib as _pl
    _repo_root = str(_pl.Path(__file__).resolve().parents[1])
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)
except Exception:
    pass

try:
    from src.router.service import RouterService
except Exception as e:
    print(json.dumps({"event": "router_diag_import_error", "error": str(e)}))
    sys.exit(1)


def main() -> int:
    rs = RouterService()
    # Preflight should not perform network calls due to ROUTER_PREFLIGHT_CHAT=false
    try:
        rs.preflight()
    except Exception as e:
        print(json.dumps({"event": "router_preflight_exception", "error": str(e)}))
        # Continue; diagnostics might still work

    scenarios: List[Dict[str, Any]] = [
        {"name": "auto_no_hint", "requested": None, "hint": None},
        {"name": "auto_moonshot_hint", "requested": "auto", "hint": {"platform": "moonshot"}},
        {"name": "auto_kimi_long", "requested": "auto", "hint": {"platform": "kimi", "task_type": "long_context_analysis"}},
        {"name": "explicit_fast", "requested": os.getenv("FAST_MODEL_DEFAULT", "glm-4.5-flash"), "hint": None},
        {"name": "explicit_unknown", "requested": "this-model-does-not-exist", "hint": None},
    ]

    results = []
    for sc in scenarios:
        try:
            dec = rs.choose_model_with_hint(sc["requested"], sc["hint"])
            results.append({
                "name": sc["name"],
                "requested": dec.requested,
                "chosen": dec.chosen,
                "reason": dec.reason,
                "provider": dec.provider,
            })
        except Exception as e:
            results.append({"name": sc["name"], "error": str(e)})

    print(json.dumps({"event": "router_diag_summary", "results": results}, ensure_ascii=False))
    # Basic sanity: we expect at least one scenario to produce a chosen model string
    ok = any(isinstance(r.get("chosen"), str) and r.get("chosen") for r in results if isinstance(r, dict))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())

