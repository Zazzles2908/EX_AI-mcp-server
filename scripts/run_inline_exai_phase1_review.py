import os, sys, asyncio
from pathlib import Path

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from mcp.types import TextContent

PHASE1_DOCS = [
    "docs/tools/analyze.md",
    "docs/tools/debug.md",
    "docs/tools/refactor.md",
    "docs/tools/secaudit.md",
    "config.py",
]
# Compute latest sweep report dynamically
SWEEP_DIR = ROOT / 'docs' / 'sweep_reports'
_latest = None
if SWEEP_DIR.exists():
    runs = [d for d in SWEEP_DIR.iterdir() if d.is_dir() and d.name not in {"phase1_exai_review"}]
    runs.sort(key=lambda p: p.name)
    if runs:
        cand = runs[-1]
        rp = cand / 'mcp_tool_sweep_report.md'
        if rp.exists():
            _latest = rp
LATEST_SWEEP = str(_latest) if _latest else "docs/mcp_tool_sweep_report.md"

async def main():
    env = {
        **os.environ,
        'PYTHONPATH': str(ROOT),
        'ENV_FILE': str(ROOT / '.env'),
        'LOG_LEVEL': os.getenv('LOG_LEVEL', 'ERROR'),
        'STREAM_PROGRESS': 'false',
    }
    params = StdioServerParameters(
        command=str(ROOT / '.venv' / 'Scripts' / 'python.exe'),
        args=['-u', 'server.py'],
        cwd=str(ROOT),
        env=env,
    )

    review_dir = ROOT / 'docs' / 'sweep_reports' / 'phase1_exai_review'
    review_dir.mkdir(parents=True, exist_ok=True)

    prompt = (
        "Review these Phase 1 docs for client-agnostic language, correctness, and clarity. "
        "Also review the latest sweep report for issues and suggest improvements. "
        f"Files: {PHASE1_DOCS + [LATEST_SWEEP]}"
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Run analyze tool for a structured review
            analyze_args = {
                'step': 'Phase 1 doc audit',
                'step_number': 1,
                'total_steps': 1,
                'next_step_required': False,
                'findings': prompt,
                'relevant_files': PHASE1_DOCS + [LATEST_SWEEP],
                'document_complexity': False,
            }
            a = await session.call_tool('analyze', analyze_args)
            a_txt = "\n\n".join(c.text for c in a.content if isinstance(c, TextContent))

            # Use docgen to create a written report from the analysis
            docgen_args = {
                'step': 'Phase 1 EXAI review',
                'step_number': 1,
                'total_steps': 1,
                'next_step_required': False,
                'findings': a_txt or prompt,
                'relevant_files': PHASE1_DOCS + [LATEST_SWEEP],
                'document_complexity': False,
                'document_flow': False,
                'update_existing': False,
                'comments_on_complex_logic': False,
                'num_files_documented': 1,
                'total_files_to_document': 1,
            }
            d = await session.call_tool('docgen', docgen_args)
            d_txt = "\n\n".join(c.text for c in d.content if isinstance(c, TextContent)) or a_txt or prompt

            out_path = review_dir / 'phase1_exai_review.md'
            out_path.write_text(d_txt, encoding='utf-8')
            print(f"Wrote Phase 1 EXAI review to {out_path}")

if __name__ == '__main__':
    asyncio.run(main())

