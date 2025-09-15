MCP Call Summary — Result: YES | Provider: GLM | Model: glm-4.5-flash | Cost: low | Duration: fast | Note: Tool Pathways QA Checklist generated

# Tool Pathways QA Checklist (chat, analyze, codereview, testgen, thinkdeep)

## Defaults to use
- Model: glm-4.5-flash (router ON, profile=balanced)
- thinking_mode: medium (bump to high only when needed)
- websearch: OFF by default (opt-in per prompt)
- SLIM_SCHEMAS=true; SECURE_INPUTS_ENFORCED=true; CHUNKED_READER_ENABLED=true

## Chat
- Acceptance checks
  - Returns within seconds on small prompts
  - MCP Call Summary shows provider=model, cost=low, duration=fast
  - Respects websearch OFF unless asked
- Small vs large files
  - Small: inline excerpt handling OK
  - Large: chunk + summarize
- Quick smoke
  - chat_exai-mcp (glm-4.5-flash) with a short prompt and 1 small file

## Analyze
- Acceptance checks
  - Produces concise findings under word budget
  - Honors thinking_mode=medium; bump to high only if complexity warrants
  - Keeps file references to absolute paths
- Small vs large files
  - Small: direct evidence lines included
  - Large: chunked summaries and clear limitations noted
- Quick smoke
  - analyze_exai-mcp on a single script; then on a folder to confirm chunking

## CodeReview (codereview)
- Acceptance checks
  - Step 1 plan; Step 2 includes NEW evidence; later steps evolve findings
  - Flags both positives and concerns
  - Avoids vague language; cites concrete files/lines
- Small vs large files
  - Small: specific diffs/smells
  - Large: focuses on hotspots, avoids full scans
- Quick smoke
  - codereview_exai-mcp step=1 with a key file; follow with 1 more step for evidence

## TestGen (testgen)
- Acceptance checks
  - Generates focused tests (unit first); names concrete functions/methods
  - Identifies happy paths and failure modes
  - Keeps scope tight (single module)
- Small vs large files
  - Small: direct cases
  - Large: prioritize critical functions; propose scaffolding
- Quick smoke
  - testgen_exai-mcp for one module; verify names match code

## ThinkDeep (thinkdeep)
- Acceptance checks
  - Provides structured reasoning with a clear final answer
  - Uses medium by default; only use high for complex multi-hop analysis
  - Keeps under timeouts; no runaway steps
- Small vs large files
  - Small: directly reasons on content
  - Large: summarize+reason pattern
- Quick smoke
  - thinkdeep with 1–2 small files; ensure final section is crisp and action-oriented

## Observability & guardrails across tools
- Always ensure MCP Call Summary is present and first
- LOG_LEVEL=INFO, LOG_FORMAT=json; STREAM_PROGRESS=true
- Respect DISABLED_TOOLS and SECURE_INPUTS_ENFORCED
- Prefer chunking over long-context models

## Acceptance gate before merging pathways work
- A) All quick smokes pass for both providers on small prompts/files
- B) At least one analyze and one codereview include concrete evidence lines
- C) testgen produces runnable test skeletons with correct names
- D) thinkdeep returns structured reasoning within timeouts

