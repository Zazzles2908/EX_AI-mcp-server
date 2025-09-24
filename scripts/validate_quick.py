# DEPRECATED SHIM — use scripts/validation/validate_quick.py
# This top-level wrapper forwards to the canonical entry point and will be removed in a future release.

# Back-compat shim: forwards to canonical subfolder
if __name__ == "__main__":
    import pathlib, runpy, sys
    target = pathlib.Path(__file__).parent / "validation" / "validate_quick.py"
    try:
        runpy.run_path(str(target), run_name="__main__")
    except SystemExit as e:
        raise
    except Exception as e:
        print(f"Shim failed to run target {target}: {e}")
        sys.exit(1)
    sys.exit(0)


# Back-compat shim: prefer canonical script in subfolder; this shim forwards and exits.
if __name__ == "__main__":
    import pathlib, runpy, sys
    target = pathlib.Path(__file__).parent / "validation" / "validate_quick.py"
    try:
        runpy.run_path(str(target), run_name="__main__")
    except SystemExit as e:
        raise
    except Exception as e:
        print(f"Shim failed to run target {target}: {e}")
        sys.exit(1)
    sys.exit(0)

import os, sys, importlib.util, json, traceback
from pathlib import Path

# Ensure project root on sys.path for src.* imports
PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# Load .env if present (and capture raw file values separately from process env)
file_env = {}
try:
    from dotenv import load_dotenv, dotenv_values
    load_dotenv(override=False)  # do not override existing process env
    file_env = dotenv_values()
except Exception:
    pass

RESULT = {"env": {}, "tools": {}, "providers": {}, "inference": {}}

# 1) Environment configuration validation
required = ["KIMI_API_KEY", "GLM_API_KEY"]
for k in required:
    # Validate presence in effective environment (process OR .env file)
    val = os.getenv(k) or file_env.get(k)
    RESULT["env"][k] = bool(val)

RESULT["env"]["DISABLED_PROVIDERS"] = (os.getenv("DISABLED_PROVIDERS") or file_env.get("DISABLED_PROVIDERS") or "")

web_vars = [
    "ENABLE_WEB_SEARCH","SEARCH_PROVIDER","BRAVE_API_KEY","TAVILY_API_KEY",
    "ENABLE_PROVIDER_WEBSEARCH","KIMI_ENABLE_INTERNET_SEARCH","GLM_ENABLE_WEB_BROWSING",
    "WEB_ALLOWLIST","WEB_DENYLIST","MAX_WEB_RESULTS","WEB_CACHE_TTL_SEC","FETCH_USER_AGENT",
]
# Only report web vars if they exist in the .env file (strict requirement)
RESULT["env"]["web_vars_present_in_env_file"] = {k: v for k, v in ((w, file_env.get(w)) for w in web_vars) if v}

# 2) Dependency isolation testing
RESULT["env"]["has_zhipuai_module"] = bool(importlib.util.find_spec("zhipuai"))

# 3) Tools and providers import
try:
    from tools.registry import ToolRegistry
    tr = ToolRegistry(); tr.build_tools()
    names = sorted(tr.list_tools().keys())
    RESULT["tools"]["loaded"] = names
    RESULT["tools"]["has_web_tools"] = any(n in ("web_search","fetch_url") for n in names)
except Exception as e:
    RESULT["tools"]["error"] = f"{type(e).__name__}: {e}"

try:
    # Minimal provider registration (mimics server logic without starting it)
    from src.providers.registry import ModelProviderRegistry
    from src.providers.base import ProviderType
    from src.providers.kimi import KimiModelProvider as _Kimi
    from src.providers.glm import GLMModelProvider as _GLM
    disabled = {p.strip().upper() for p in (os.getenv("DISABLED_PROVIDERS") or file_env.get("DISABLED_PROVIDERS") or "").split(",") if p.strip()}
    if (os.getenv("KIMI_API_KEY") or file_env.get("KIMI_API_KEY")) and "KIMI" not in disabled:
        ModelProviderRegistry.register_provider(ProviderType.KIMI, _Kimi)
    if (os.getenv("GLM_API_KEY") or file_env.get("GLM_API_KEY")) and "GLM" not in disabled:
        ModelProviderRegistry.register_provider(ProviderType.GLM, _GLM)
    RESULT["providers"]["with_keys"] = [p.value for p in ModelProviderRegistry.get_available_providers_with_keys()]
    # Smoke get providers
    g = ModelProviderRegistry.get_provider(ProviderType.GLM)
    k = ModelProviderRegistry.get_provider(ProviderType.KIMI)
    RESULT["providers"]["has_glm_provider"] = g is not None
    RESULT["providers"]["has_kimi_provider"] = k is not None
    # Detect optional SDK in GLM provider instance if created
    if g is not None:
        RESULT["providers"]["glm_uses_sdk"] = bool(getattr(g, "_zhipu_sdk_client", None))
except Exception as e:
    RESULT["providers"]["error"] = f"{type(e).__name__}: {e}"

# 4) Core functionality (minimal inference, safe time/size)
# Note: Will attempt network calls; failures are captured.

def _try_completion(ptype, model, prompt):
    from src.providers.registry import ModelProviderRegistry
    from src.providers.base import ProviderType
    prov = ModelProviderRegistry.get_provider(getattr(ProviderType, ptype))
    if not prov:
        return {"ok": False, "error": "provider_unavailable"}
    try:
        resp = prov.generate_content(
            prompt=prompt,
            model_name=model,
            system_prompt=None,
            temperature=0.3,
            max_output_tokens=32,
        )
        return {"ok": True, "content": (resp.content[:120] if getattr(resp, "content", None) else ""), "metadata": getattr(resp, "metadata", {})}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

# Models: use defaults expected by repo
RESULT["inference"]["glm"] = _try_completion("GLM", (os.getenv("DEFAULT_MODEL") or file_env.get("DEFAULT_MODEL") or "glm-4.5-flash"), "ping")
RESULT["inference"]["kimi"] = _try_completion("KIMI", (os.getenv("KIMI_SPEED_MODEL") or file_env.get("KIMI_SPEED_MODEL") or "kimi-k2-0711-preview"), "ping")

print(json.dumps(RESULT, indent=2))

