import os
import sys
import json
import asyncio
from pathlib import Path

# Ensure project root on path regardless of cwd
PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from tools.registry import ToolRegistry, TOOL_MAP  # type: ignore
from mcp.types import TextContent  # type: ignore

# Load environment (.env) so providers/keys are available when running directly
try:
    from dotenv import load_dotenv  # type: ignore
    _env_path = os.getenv("ENV_FILE") or str(PROJECT_DIR / ".env")
    load_dotenv(_env_path)
except Exception:
    pass

# Ensure providers are configured similarly to server runtime
try:
    from server import _ensure_providers_configured  # type: ignore
    _ensure_providers_configured()
except Exception:
    pass

# Resolve available models and pick sensible defaults/fallbacks
try:
    from src.providers.registry import ModelProviderRegistry  # type: ignore
    from src.providers.base import ProviderType  # type: ignore
    _avail_kimi = list(ModelProviderRegistry.get_available_model_names(provider_type=ProviderType.KIMI))
    _avail_glm = list(ModelProviderRegistry.get_available_model_names(provider_type=ProviderType.GLM))
except Exception:
    _avail_kimi, _avail_glm = [], []

_req_kimi = os.getenv("ASSESS_KIMI_MODEL", "kimi-k2-0711-preview")
_req_glm = os.getenv("ASSESS_GLM_MODEL", "glm-4.5-flash")

def _choose_model(requested: str, available: list[str], fallback: str | None = None) -> str | None:
    if not available:
        return None
    if requested in available:
        return requested
    if fallback and fallback in available:
        return fallback
    return available[0]

KIMI_MODEL = _choose_model(_req_kimi, _avail_kimi, fallback="kimi-k2-0711-preview")
GLM_MODEL = _choose_model(_req_glm, _avail_glm, fallback="glm-4.5-flash")

print(f"[ASSESS] Detected Kimi models: {_avail_kimi or []}; chosen: {KIMI_MODEL}")
print(f"[ASSESS] Detected GLM models: {_avail_glm or []}; chosen: {GLM_MODEL}")

OUT_DIR = PROJECT_DIR / "assessments"
JSON_DIR = OUT_DIR / "json"
MD_PATH = OUT_DIR / "ALL_TOOLS_ASSESSMENT.md"
JSON_DIR.mkdir(parents=True, exist_ok=True)


def get_tool_source_file(tool_name: str) -> str:
    """Resolve the python file path for a tool using TOOL_MAP."""
    mod, cls = TOOL_MAP.get(tool_name, (None, None))
    if not mod:
        return ""
    try:
        m = __import__(mod, fromlist=[cls])
        path = Path(m.__file__).resolve()
        return str(path)
    except Exception:
        return ""


async def run_tool_async(tool, arguments: dict) -> dict:
    try:
        res = await tool.execute(arguments)
        if isinstance(res, list) and res:
            # Prefer first TextContent; if none, use stringified content
            txt = None
            for item in res:
                if isinstance(item, TextContent):
                    txt = item.text
                    break
            if txt is None:
                txt = str(res[0])
            # Try strict JSON first
            try:
                return json.loads(txt)
            except Exception:
                # Heuristic: extract first JSON object substring
                try:
                    start = txt.find('{')
                    if start != -1:
                        candidate = txt[start:]
                        return json.loads(candidate)
                except Exception:
                    pass
                return {"status": "error", "error": "Response was not valid JSON", "raw": txt[:2000]}
        return {"status": "error", "error": "Unexpected tool return"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def analyze_tool(tool_name: str, source_file: str, model: str) -> dict:
    from tools.analyze import AnalyzeTool  # lazy import

    analyze = AnalyzeTool()
    args = {
        "model": model,
        "step": f"Assess the {tool_name} tool implementation for flaws, inefficiencies, instability, and UX complexity risks.",
        "step_number": 1,
        "total_steps": 1,
        "next_step_required": False,
        "findings": "",
        "relevant_files": [source_file] if source_file else [],
        # Keep defaults for analysis_type/general
    }
    return await run_tool_async(analyze, args)


async def run_consensus(tool_name: str, kimi_json: dict, glm_json: dict) -> dict:
    """Drive ConsensusTool across required steps with both models neutral."""
    from tools.consensus import ConsensusTool  # lazy import

    # Prepare proposal step content
    proposal = {
        "tool": tool_name,
        "constraints": [
            "Keep user-facing UX clean and simple; tools are used AI-to-AI",
            "Improve effectiveness and stability",
        ],
        "kimi_assess": kimi_json,
        "glm_assess": glm_json,
    }
    step_text = (
        "Evaluate the improvement plan for tool '" + tool_name + "' based on the two assessments below. "
        "Return a concise set of improvements that balance simplicity (AI-to-AI UX) and effectiveness/stability. "
        "When relevant, propose small interface tweaks to keep inputs/outputs minimal and deterministic.\n\n" + json.dumps(proposal, ensure_ascii=False)
    )

    consensus = ConsensusTool()

    # Step 1: provide our analysis and seed models list
    models = [
        {"model": KIMI_MODEL, "stance": "neutral"},
        {"model": GLM_MODEL, "stance": "neutral"},
    ]
    args = {
        "step": step_text,
        "step_number": 1,
        "total_steps": len(models),
        "next_step_required": True,
        "findings": f"Assessment analysis for {tool_name} tool based on Kimi and GLM evaluations.",
        "models": models,
    }
    out = await run_tool_async(consensus, args)
    cont_id = out.get("continuation_id")

    # Iterate per-model steps until done or we reach total steps
    for i in range(2, len(models) + 1):
        args = {
            "step": f"Continue consensus for {tool_name} (step {i}).",
            "step_number": i,
            "total_steps": len(models),
            "next_step_required": (i < len(models)),
            "continuation_id": cont_id,
        }
        out = await run_tool_async(consensus, args)
        cont_id = out.get("continuation_id", cont_id)

    return out


def summarise_for_md(label: str, data: dict) -> str:
    try:
        return f"### {label}\n\n" + "```json\n" + json.dumps(data, indent=2, ensure_ascii=False) + "\n```\n\n"
    except Exception:
        return f"### {label}\n\n(Unable to serialize)\n\n"


async def main():
    reg = ToolRegistry(); reg.build_tools()
    tools = sorted(reg.list_tools().keys())

    report_sections = []
    index_entries = []

    for name in tools:
        # Skip internal-only utilities if any slipped through
        if name in {"toolcall_log_tail"}:
            continue

        src_file = get_tool_source_file(name)
        print(f"[ASSESS] {name} -> {src_file}")

        kimi_res = await analyze_tool(name, src_file, KIMI_MODEL)
        glm_res = await analyze_tool(name, src_file, GLM_MODEL)

        # Persist raw json per tool
        with (JSON_DIR / f"{name}.kimi.json").open("w", encoding="utf-8") as f:
            json.dump(kimi_res, f, indent=2, ensure_ascii=False)
        with (JSON_DIR / f"{name}.glm.json").open("w", encoding="utf-8") as f:
            json.dump(glm_res, f, indent=2, ensure_ascii=False)

        # Run consensus for this tool
        consensus_res = await run_consensus(name, kimi_res, glm_res)
        with (JSON_DIR / f"{name}.consensus.json").open("w", encoding="utf-8") as f:
            json.dump(consensus_res, f, indent=2, ensure_ascii=False)

        # Build MD section
        index_entries.append(f"- [{name}](#{name.replace('_','-')})")
        section = [f"## {name}\n\n"]
        section.append(summarise_for_md("Kimi assessment", kimi_res))
        section.append(summarise_for_md("GLM assessment", glm_res))
        section.append(summarise_for_md("Consensus recommendations", consensus_res))
        report_sections.append("".join(section))

    md = [
        "# EXAI Assessment: All Tools (Kimi & GLM + Consensus)\n\n",
        "Note: Keep UX clean/simple (AI-to-AI) while improving effectiveness and stability.\n\n",
        "## Index\n\n",
        "\n".join(index_entries) + "\n\n",
        "---\n\n",
        "\n\n".join(report_sections),
    ]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with MD_PATH.open("w", encoding="utf-8") as f:
        f.write("".join(md))

    print(f"Written: {MD_PATH}")


if __name__ == "__main__":
    asyncio.run(main())

