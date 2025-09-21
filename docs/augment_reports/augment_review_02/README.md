# augment_review_02

Branch: feat/mcp-tools-stabilization-2025-09-21

Purpose
- Consolidate EXAI-MCP findings and plans for stabilizing MCP tools (chat/analyze stable; others currently broken)
- Align with Tools Reorg Proposal (2025-09-20) and proposed document structure
- Track validation runs (router checks, diagnostics, unpredictable-prompt smokes)

Inputs reviewed
- docs/augment_reports/architecture/tools_reorg_proposal_2025-09-20.md
- docs/augment_reports/augment_review/exai_ws_mcp_outputs_kimi_2025-09-21.md
- docs/augment_reports/augment_review/exai_ws_mcp_outputs_2025-09-21.md
- docs/augment_reports/augment_review/proposed_document_structure_2025-09-20.md

Artifacts to be added here
- initial_plan_2025-09-21.md (prioritized approach + 30/60/90 + checklist)
- exai_chat_summary_2025-09-21.md (raw EXAI MCP chat output)
- exai_analyze_kickoff_2025-09-21.md (EXAI MCP analyze step outputs)

Notes
- Universal UI wrapper: implement server-level ui_summary addition (non-destructive)
- Registry-first: fix argument schemas and visibility; defer file moves until smokes are green
- Provider orchestration: keep GLM manager-first with parallel GLM web + Kimi files when needed

