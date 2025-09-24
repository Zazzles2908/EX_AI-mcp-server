#!/usr/bin/env python3
"""
Simplified config migration (dry-run).
Reads .env, writes .env.new with a reduced, organized set of variables.
Does NOT modify your existing .env.
"""
from __future__ import annotations

import os
from pathlib import Path

MAP = {
    # Core providers
    "KIMI_API_KEY": "KIMI_API_KEY",
    "GLM_API_KEY": "GLM_API_KEY",
    # Model defaults
    "DEFAULT_MODEL": "DEFAULT_MODEL",
    "KIMI_DEFAULT_MODEL": "KIMI_DEFAULT_MODEL",
    "GLM_FLASH_MODEL": "GLM_DEFAULT_MODEL",
    # Features (best-effort mappings)
    "EX_WEBSEARCH_ENABLED": "ENABLE_WEB_SEARCH",
    # Timeouts
    "EX_TOOL_TIMEOUT_SECONDS": "TOOL_TIMEOUT",
    "KIMI_MF_CHAT_TIMEOUT_SECS": "PROVIDER_TIMEOUT",
    # Server
    "MCP_SERVER_NAME": "MCP_SERVER_NAME",
    "EXAI_WS_HOST": "EXAI_WS_HOST",
    "EXAI_WS_PORT": "EXAI_WS_PORT",
}

HEADER = """# === EX-AI MCP Server - Simplified Configuration (Generated) ===
# Review and copy into your .env when ready.
"""

def read_env(path: Path) -> dict:
    data = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        data[k.strip()] = v
    return data


def main() -> None:
    old_env = Path(".env")
    out = Path(".env.new")
    src = read_env(old_env)

    lines = [HEADER]
    lines.append("# === CORE PROVIDER KEYS (Required) ===")
    lines.append(f"KIMI_API_KEY={src.get('KIMI_API_KEY', '')}")
    lines.append(f"GLM_API_KEY={src.get('GLM_API_KEY', '')}")
    lines.append("")

    lines.append("# === MODEL DEFAULTS ===")
    lines.append(f"DEFAULT_MODEL={src.get('DEFAULT_MODEL', 'auto')}")
    lines.append(f"KIMI_DEFAULT_MODEL={src.get('KIMI_DEFAULT_MODEL', 'kimi-k2-0905-preview')}")
    lines.append(f"GLM_DEFAULT_MODEL={src.get('GLM_FLASH_MODEL', 'glm-4.5-flash')}")
    lines.append("GLM_QUALITY_MODEL=glm-4.5")
    lines.append("KIMI_QUALITY_MODEL=kimi-k2-0905-preview")
    lines.append("")

    lines.append("# === CORE FEATURES ===")
    lines.append(f"ENABLE_AI_MANAGER={'true' if src.get('EX_AI_MANAGER_ENABLED','false').lower() in {'1','true','yes','on'} else 'false'}")
    lines.append(f"ENABLE_WEB_SEARCH={'true' if src.get('EX_WEBSEARCH_ENABLED','true').lower() in {'1','true','yes','on'} else 'false'}")
    lines.append("ENABLE_FILE_UPLOAD=true")
    lines.append("ENABLE_FALLBACK=true")
    lines.append("")

    lines.append("# === TIMEOUTS (Seconds) ===")
    lines.append(f"TOOL_TIMEOUT={src.get('EX_TOOL_TIMEOUT_SECONDS', '120')}")
    lines.append(f"PROVIDER_TIMEOUT={src.get('KIMI_MF_CHAT_TIMEOUT_SECS', '60')}")
    lines.append("UPLOAD_TIMEOUT=180")
    lines.append("")

    lines.append("# === SERVER CONFIG ===")
    lines.append(f"MCP_SERVER_NAME={src.get('MCP_SERVER_NAME','exai')}")
    lines.append(f"EXAI_WS_HOST={src.get('EXAI_WS_HOST','127.0.0.1')}")
    lines.append(f"EXAI_WS_PORT={src.get('EXAI_WS_PORT','8765')}")
    lines.append("LOG_LEVEL=INFO")
    lines.append("")

    lines.append("# === OPTIONAL PROVIDERS ===")
    lines.append("OPENROUTER_API_KEY=")
    lines.append("CUSTOM_API_URL=")
    lines.append("")

    lines.append("# === ADVANCED (Optional) ===")
    lines.append("MAX_FILE_SIZE_MB=100")
    lines.append("MAX_CONTEXT_TOKENS=128000")
    lines.append("ENABLE_CACHING=true")
    lines.append("CACHE_TTL_HOURS=24")
    lines.append("")

    lines.append("# === Moonshot (Kimi) OpenAI-compatible base_url ===")
    lines.append("OPENAI_BASE_URL=https://api.moonshot.ai/v1")
    lines.append("")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out} (dry-run). Review and replace your .env when ready.")


if __name__ == "__main__":
    main()

