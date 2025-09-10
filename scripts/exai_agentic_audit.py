import os
import sys
import json
import argparse
from typing import List
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
except Exception:
    pass

# Run through the MCP server tools so that real providers/models are used
# Ensure repository root is on sys.path
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    import server  # noqa: F401
    from server import handle_call_tool
    # Ensure providers are configured when running as a standalone script
    try:
        server.configure_providers()
    except Exception as _e:
        # Non-fatal: downstream tools will attempt their own selection/fallback
        print(f"Provider configuration warning: {_e}")
except Exception as e:
    print("Failed to import MCP server: ", e)
    sys.exit(1)


DEFAULT_FILES = [
    "server.py",
    "tools/consensus.py",
    "providers/registry.py",
    "README.md",
]

STRICT_JSON_SPEC = (
    "Return STRICT JSON only (no prose). Schema: {\\n"
    "  \\\"issues\\\": [ { \\\"title\\\": string, \\\"evidence\\\": string, \\\"direct_fix\\\": string } ],\\n"
    "  \\\"summary\\\": string\\n"
    "}"
)

BASE_AUDIT_PROMPT = (
    "Audit EX MCP server. Focus areas: (1) hidden router boundary logs + resolver hook, "
    "(2) consensus ModelContext injection, (3) provider allowlists vs providers/*, "
    "(4) agentic fallback to chat/kimi when consensus fails, (5) Windows-friendly paths/sys.path/.env load. "
)


def _read_snippet(path: str, max_chars: int = 1600) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
        # Heuristic: prefer blocks around keywords
        keys = [
            "boundary_model_resolution_attempt",
            "boundary_model_resolved",
            "ModelContext",
            "load_dotenv",
            "get_available_models",
            "agentic",
        ]
        best = ""
        for k in keys:
            idx = data.find(k)
            if idx != -1:
                start = max(0, idx - max_chars // 2)
                end = min(len(data), idx + max_chars // 2)
                best = data[start:end]
                break
        if not best:
            best = data[:max_chars]
        if len(best) > max_chars:
            best = best[:max_chars]
        return f"[FILE {path}]\n" + best + "\n[END FILE]\n"
    except Exception as e:
        return f"[FILE {path}]\n<error reading file: {e}>\n[END FILE]\n"


def _build_audit_prompt(files: List[str], max_total_chars: int = 4800) -> str:
    prompt = [BASE_AUDIT_PROMPT, "\n", STRICT_JSON_SPEC, "\n\nContext excerpts:\n"]
    used = 0
    for p in files:
        if not os.path.exists(p):
            continue
        remain = max_total_chars - used
        if remain <= 200:
            break
        snip = _read_snippet(p, max_chars=min(1600, remain))
        used += len(snip)
        prompt.append(snip)
    return "".join(prompt)


def _try_parse_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except Exception:
        return None


def _accepts_schema(j: dict | None) -> bool:
    return bool(j and isinstance(j, dict) and isinstance(j.get("issues"), list) and isinstance(j.get("summary"), str))


def _fallback_chat_only_json(audit_prompt: str) -> dict | None:
    chat_out = run_tool("chat", {
        "prompt": audit_prompt + "\n" + STRICT_JSON_SPEC + "\nOnly JSON.",
        "model": "auto",
    })
    texts = [getattr(c, "text", getattr(c, "content", None)) for c in chat_out]
    for t in reversed(texts):
        j = _try_parse_json(t) if isinstance(t, str) else None
        if _accepts_schema(j):
            return j
    return None


def _fallback_kimi(files: List[str], audit_prompt: str) -> dict | None:
    # Try to upload minimal files then ask for strict JSON
    existing = [os.path.abspath(p) for p in files if os.path.exists(p)]
    if not existing:
        existing = []
    try:
        if existing:
            _ = run_tool("kimi_upload_and_extract", {"files": existing})
        chat = run_tool("kimi_chat_with_tools", {
            "messages": [
                {"role":"system","content":"You are EX-AI analysis agent. Strict JSON only."},
                {"role":"user","content": audit_prompt + "\n" + STRICT_JSON_SPEC + "\nOnly JSON."}
            ],
        })
        texts = [getattr(c, "text", getattr(c, "content", None)) for c in chat]
        for t in reversed(texts):
            # kimi_chat_with_tools returns raw provider JSON as text
            base = _try_parse_json(t) if isinstance(t, str) else None
            if isinstance(base, dict):
                try:
                    choices = base.get("choices") or []
                    if choices:
                        content = choices[0].get("message", {}).get("content")
                        jj = _try_parse_json(content) if isinstance(content, str) else None
                        if _accepts_schema(jj):
                            return jj
                except Exception:
                    pass
            # Also accept direct JSON
            if _accepts_schema(base):
                return base
    except Exception:
        pass
    return None


def run_consensus(models: List[str], files: List[str]) -> dict:
    # Build an inline, small prompt to avoid large file embedding
    inline_prompt = _build_audit_prompt(files)

    # Step 1 records the proposal
    step1_args = {
        "step": inline_prompt,
        "step_number": 1,
        "total_steps": len(models),
        "next_step_required": True,
        "findings": "",
        "models": [{"model": m, "stance": "neutral"} for m in models],
        # Avoid relevant_files to prevent auto-embedding
        "relevant_files": [],
    }
    _ = run_tool("consensus", step1_args)

    # Step 2..N: consult each model
    out = None
    for i, m in enumerate(models, start=1):
        step_args = {
            "step": f"Consult model: {m}",
            "step_number": i,
            "total_steps": len(models),
            "next_step_required": i < len(models),
            "findings": "",
            "models": [{"model": m, "stance": "neutral"}],
            "current_model_index": i,
            "relevant_files": [],
        }
        out_chunks = run_tool("consensus", step_args)
        out_texts = [getattr(c, "text", getattr(c, "content", None)) for c in out_chunks]
        out = out_texts[-1] if out_texts else None

    if isinstance(out, str):
        j = _try_parse_json(out)
        if _accepts_schema(j):
            return j
        # Fallback 1: Chat with auto model
        j = _fallback_chat_only_json(inline_prompt)
        if _accepts_schema(j):
            return j
        # Fallback 2: Kimi tools with messages array
        j = _fallback_kimi(files, inline_prompt)
        if _accepts_schema(j):
            return j
        return {"raw": out}
    return {"raw": out}


def run_tool(name: str, args: dict):
    try:
        return run_sync(handle_call_tool(name, args))
    except Exception as e:
        return [type("C", (), {"text": f"ERROR calling {name}: {e}"})()]


def run_sync(coro):
    import asyncio
    try:
        # Preferred: use a fresh event loop if none is set (avoids DeprecationWarning on Windows)
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop: create one explicitly
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            try:
                loop.close()
            except Exception:
                pass
    else:
        # A loop is already running (rare for this CLI); fall back to asyncio.run if possible
        # but since we cannot nest asyncio.run, schedule the task and wait synchronously
        return asyncio.create_task(coro)


def main():
    parser = argparse.ArgumentParser(description="EX-AI agentic audit (consensus-based) using real models")
    parser.add_argument("--models", nargs="*", default=[
        os.getenv("GLM_AUDIT_MODEL", "glm-4.5-air"),
        os.getenv("KIMI_AUDIT_MODEL", "kimi-k2-0905-preview"),
    ], help="Models to consult (default: GLM + Kimi)")
    parser.add_argument("--files", nargs="*", default=DEFAULT_FILES, help="Files to include as context")
    args = parser.parse_args()

    print("Consulting models:", args.models)
    print("Context files:", [p for p in args.files if os.path.exists(p)])

    result = run_consensus(args.models, args.files)

    print("\n=== EX-AI MCP Audit Report ===")
    if isinstance(result, dict) and "issues" in result:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Model did not return structured JSON. Raw output:")
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

