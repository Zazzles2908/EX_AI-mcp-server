# Tools consolidation (design + gated scaffold) — Batch 7

One-liner: YES — smart_chat scaffold exists (advisory only), file_chat scaffold added; registry unchanged (not wired).

## Actions
- Verified tools/smart/smart_chat.py scaffold (advisory only, no routing changes)
- Added tools/smart/file_chat.py scaffold to normalize files+prompt into messages (advisory only)
- Left tools/registry.py unchanged (no new wiring); gating remains external

## Next
- If/when enabled, add registry entry behind ENABLE_SMART_CHAT flag and keep visibility as user-visible with advisory docs
- Validate with EXAI‑MCP baseline suite; ensure MCP_CALL_SUMMARY lines appear for smart_chat/file_chat

