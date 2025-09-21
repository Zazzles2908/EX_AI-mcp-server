# Copy of scripts/run_kimi_glm_audit_v4.py under scripts/kimi_analysis
from __future__ import annotations
import datetime, json, os
from pathlib import Path
from typing import Any, Dict, List
REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs" / "sweep_reports" / "phase3_exai_review"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
FILES_TO_AUDIT = ["src/providers/openai_compatible.py","src/providers/glm.py","src/providers/kimi.py","src/providers/custom.py","src/providers/openrouter.py","utils/http_client.py","tools/glm_files.py"]
import sys; sys.path.insert(0, str(REPO_ROOT))
from src.providers.kimi import KimiModelProvider  # type: ignore
from src.providers.glm import GLMModelProvider  # type: ignore
from src.providers.registry import ModelProviderRegistry  # type: ignore
PROMPT = ("You are a senior Python reviewer. Audit these modified files.\nFocus on correctness, safety, adherence to provider APIs (Kimi/Moonshot, ZhipuAI GLM),\nerror handling and retries, streaming paths, and consistency with an OpenAI-compatible\nsurface. Identify any issues, risks, or follow-ups that would improve reliability.\nReturn a concise, prioritized bullet list and short rationale.")

def run_kimi(files: List[str]) -> Dict[str, Any]:
    api_key = os.getenv("KIMI_API_KEY");
    if not api_key: return {"skipped": True, "reason": "KIMI_API_KEY not set"}
    prov = ModelProviderRegistry.get_provider_for_model(os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview"))
    if not isinstance(prov, KimiModelProvider): prov = KimiModelProvider(api_key=api_key)
    sys_msgs: List[Dict[str, Any]] = []
    for fp in files:
        file_id = prov.upload_file(fp, purpose="file-extract")
        content = prov.client.files.content(file_id=file_id).text
        sys_msgs.append({"role":"system","content":content,"_file_id":file_id})
    model = os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview"); temperature = float(os.getenv("KIMI_DEFAULT_TEMPERATURE", "0.3"))
    messages = [*sys_msgs, {"role":"user","content":PROMPT}]
    resp = prov.client.chat.completions.create(model=model, messages=messages, temperature=temperature)
    content = resp.choices[0].message.content
    return {"skipped": False, "result": {"model": model, "content": content}}

def run_glm(files: List[str]) -> Dict[str, Any]:
    api_key = os.getenv("GLM_API_KEY");
    if not api_key: return {"skipped": True, "reason": "GLM_API_KEY not set"}
    model = os.getenv("GLM_QUALITY_MODEL", "glm-4.5")
    prov = ModelProviderRegistry.get_provider_for_model(model)
    if not isinstance(prov, GLMModelProvider): prov = GLMModelProvider(api_key=api_key)
    uploaded: List[Dict[str, Any]] = []
    for fp in files:
        file_id = prov.upload_file(fp, purpose="agent"); uploaded.append({"file_id": file_id, "filename": Path(fp).name})
    sys_msg = "\n".join([f"[GLM Uploaded] {u['filename']} (id={u['file_id']})" for u in uploaded])
    mr = prov.generate_content(prompt=PROMPT, model_name=model, system_prompt=sys_msg, temperature=0.3)
    return {"skipped": False, "result": {"model": model, "content": mr.content, "uploaded": uploaded}}

def main() -> None:
    files = [str((REPO_ROOT / p).resolve()) for p in FILES_TO_AUDIT if (REPO_ROOT / p).exists()]
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"); report_path = DOCS_DIR / f"{ts}_exai_live_audit_v5.md"
    sections: List[str] = []; sections.append("## EXAI Live Audit (v5)\n"); sections.append("### Inputs (files)\n")
    for f in files: sections.append(f"- {Path(f).relative_to(REPO_ROOT)}\n")
    kimi_out = run_kimi(files); sections.append("\n### Kimi audit\n");
    if kimi_out.get("skipped"): sections.append(f"- Skipped: {kimi_out.get('reason')}\n")
    else:
        res = kimi_out["result"]; sections.append(f"- Model: {res.get('model')}\n"); sections.append("- Response:\n\n"); sections.append(res.get("content", "")); sections.append("\n")
    glm_out = run_glm(files); sections.append("\n### GLM audit\n")
    if glm_out.get("skipped"): sections.append(f"- Skipped: {glm_out.get('reason')}\n")
    else:
        res = glm_out["result"]; sections.append(f"- Model: {res.get('model')}\n"); uploaded = res.get("uploaded");
        if uploaded:
            sections.append("- Uploaded files:\n");
            for u in uploaded: sections.append(f"  - {u.get('filename')} (id={u.get('file_id')})\n")
        sections.append("- Response:\n\n"); sections.append(res.get("content", "")); sections.append("\n")
    report_path.write_text("\n".join(sections), encoding="utf-8"); print(str(report_path.relative_to(REPO_ROOT)))
if __name__ == "__main__":
    main()

