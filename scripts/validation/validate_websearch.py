# Copy of scripts/validate_websearch.py under scripts/validation
import os, sys, json, asyncio, logging
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.abspath(os.getcwd()))
from tools.registry import ToolRegistry
LOG_LEVEL = os.getenv("VALIDATION_LOG_LEVEL", "WARNING").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.WARNING))
if os.getenv("VALIDATION_SHORT_TIMEOUTS", "true").strip().lower() == "true":
    os.environ.setdefault("CUSTOM_CONNECT_TIMEOUT", "10")
    os.environ.setdefault("CUSTOM_READ_TIMEOUT", "60")
    os.environ.setdefault("CUSTOM_WRITE_TIMEOUT", "60")
    os.environ.setdefault("CUSTOM_POOL_TIMEOUT", "60")
tr = ToolRegistry(); tr.build_tools(); chat = tr.get_tool('chat')
try:
    from src.providers.registry import ModelProviderRegistry
    from src.providers.base import ProviderType
    from src.providers.kimi import KimiModelProvider as _Kimi
    from src.providers.glm import GLMModelProvider as _GLM
    disabled = {p.strip().upper() for p in (os.getenv("DISABLED_PROVIDERS") or "").split(",") if p.strip()}
    if (os.getenv("KIMI_API_KEY")) and "KIMI" not in disabled:
        ModelProviderRegistry.register_provider(ProviderType.KIMI, _Kimi)
    if (os.getenv("GLM_API_KEY")) and "GLM" not in disabled:
        ModelProviderRegistry.register_provider(ProviderType.GLM, _GLM)
    providers_with_keys = set(ModelProviderRegistry.get_available_providers_with_keys())
except Exception as e:
    print("provider_registration_error:", type(e).__name__, e); providers_with_keys = set()
KIMI_CANDIDATES = ["kimi-k2-turbo-preview", "kimi-k2-0711-preview"]
GLM_CANDIDATES = ["glm-4.5-air", "glm-4.5-flash", "glm-4.5"]

def select_model(provider_type, env_var, candidates):
    info = {"env_override": os.getenv(env_var), "available": [], "selected": None, "provider_has_key": provider_type in providers_with_keys, "disabled": False}
    try:
        available = ModelProviderRegistry.get_available_model_names(provider_type)
    except Exception:
        available = []
    info["available"] = available
    if info["env_override"] and info["env_override"] in available: info["selected"] = info["env_override"]; return info["selected"], info
    for c in candidates:
        if c in available: info["selected"] = c; return c, info
    return None, info

from src.providers.base import ProviderType
kimi_model, kimi_info = select_model(ProviderType.KIMI, "KIMI_SPEED_MODEL", KIMI_CANDIDATES)
glm_model, glm_info = select_model(ProviderType.GLM, "DEFAULT_MODEL", GLM_CANDIDATES)

results = {"env": {"KIMI_ENABLE_INTERNET_SEARCH": os.getenv("KIMI_ENABLE_INTERNET_SEARCH"), "GLM_ENABLE_WEB_BROWSING": os.getenv("GLM_ENABLE_WEB_BROWSING"), "CUSTOM_CONNECT_TIMEOUT": os.getenv("CUSTOM_CONNECT_TIMEOUT"), "CUSTOM_READ_TIMEOUT": os.getenv("CUSTOM_READ_TIMEOUT"), "EX_TOOLCALL_LOG_PATH": os.getenv("EX_TOOLCALL_LOG_PATH"), "EX_TOOLCALL_REDACTION": os.getenv("EX_TOOLCALL_REDACTION"), "EX_WEBSEARCH_CACHE_TTL_S": os.getenv("EX_WEBSEARCH_CACHE_TTL_S")}, "provider_status": {"KIMI": kimi_info, "GLM": glm_info}, "runs": {}}

async def _run(label, model, use_web):
    try:
        out = await chat.execute({"prompt": f"probe {label} use_websearch={use_web}", "model": model, "use_websearch": use_web, "temperature": 0.3})
        ok = isinstance(out, list) and len(out) > 0
        try:
            from mcp.types import TextContent
            if ok and isinstance(out[0], TextContent):
                txt = "".join([c.text or "" for c in out if isinstance(c, TextContent)])
                return {"ok": ok, "len": len(txt), "content_types": [type(c).__name__ for c in out]}
        except Exception:
            pass
        return {"ok": ok, "len": None}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

async def main():
    tasks = []
    if kimi_info["provider_has_key"] and kimi_info.get("selected"):
        tasks.append(("kimi_web_true", _run("kimi", kimi_info["selected"], True)))
        tasks.append(("kimi_web_false", _run("kimi", kimi_info["selected"], False)))
    else:
        results["runs"]["kimi_web_true"] = {"skipped": True, "reason": "KIMI provider unavailable or no model selectable"}
        results["runs"]["kimi_web_false"] = {"skipped": True, "reason": "KIMI provider unavailable or no model selectable"}
    if glm_info["provider_has_key"] and glm_info.get("selected"):
        tasks.append(("glm_web_true", _run("glm", glm_info["selected"], True)))
        tasks.append(("glm_web_false", _run("glm", glm_info["selected"], False)))
    else:
        results["runs"]["glm_web_true"] = {"skipped": True, "reason": "GLM provider unavailable or no model selectable"}
        results["runs"]["glm_web_false"] = {"skipped": True, "reason": "GLM provider unavailable or no model selectable"}
    if tasks:
        names, coros = zip(*tasks)
        outs = await asyncio.gather(*coros, return_exceptions=False)
        for name, out in zip(names, outs): results["runs"][name] = out
    print(json.dumps(results, indent=2))
    if os.getenv("VALIDATION_STRICT", "false").strip().lower() == "true":
        any_fail = any(v.get("ok") is False for v in results["runs"].values() if isinstance(v, dict) and "ok" in v)
        misconfigured = False
        if kimi_info["provider_has_key"] and not kimi_info.get("selected"): misconfigured = True
        if glm_info["provider_has_key"] and not glm_info.get("selected"): misconfigured = True
        if ProviderType.KIMI not in providers_with_keys: misconfigured = True
        if ProviderType.GLM not in providers_with_keys: misconfigured = True
        if any_fail or misconfigured: sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

