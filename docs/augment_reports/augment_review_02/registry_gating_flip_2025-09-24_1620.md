# Registry Gating Flip — Batch B

One-liner: YES — Gating enabled (core-only); server restarted; active tools list matches core set; awaiting single Augment restart to refresh client registry.

## Env changes
- TOOLS_CORE_ONLY=true
- TOOLS_ALLOWLIST= (empty)

## Server evidence (mcp_server.log)
- Registry gating: core_only=True allowlist=[]
- Lean tool registry active - tools: ['activity', 'analyze', 'chat', 'codereview', 'debug', 'health', 'listmodels', 'precommit', 'refactor', 'secaudit', 'testgen', 'thinkdeep', 'tracer', 'version']

## Notes
- Diagnostics preserved: version, listmodels included in core set
- Auggie wrappers remain advisory and do not expand the visible registry under gating

## Next step
- User: Restart Augment settings/extension once to refresh the tool registry
- Then: I will run final gated-registry validation and mark the task complete

