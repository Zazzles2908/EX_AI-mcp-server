# Feature Flags and Safe Enablement

This server ships with several feature flags that are OFF by default. Enabling any flag should not break
existing behavior; each is designed to be opt-in. Set flags via environment variables ("true"/"false").

## Core agentic flags (OFF by default)
- AGENTIC_ENGINE_ENABLED
- ROUTER_ENABLED
- CONTEXT_MANAGER_ENABLED
- RESILIENT_ERRORS_ENABLED
- SECURE_INPUTS_ENFORCED

## Activity tool flags (OFF by default)
- ACTIVITY_SINCE_UNTIL_ENABLED
  - Enables optional `since` / `until` request fields (ISO8601)
  - When disabled or fields omitted, behavior is unchanged
- ACTIVITY_STRUCTURED_OUTPUT_ENABLED
  - Enables optional `structured: true` request field
  - When enabled and `structured: true`, returns JSONL (one JSON record per line)

## Examples

Windows PowerShell:
```
$env:ACTIVITY_SINCE_UNTIL_ENABLED = "true"
$env:ACTIVITY_STRUCTURED_OUTPUT_ENABLED = "true"
```

Linux/macOS:
```
export ACTIVITY_SINCE_UNTIL_ENABLED=true
export ACTIVITY_STRUCTURED_OUTPUT_ENABLED=true
```

## Verification
- With all flags OFF: tools behave exactly as before
- With Activity flags ON:
  - activity with `since`/`until` filters lines to the requested time window (best-effort timestamp parsing)
  - activity with `structured: true` returns JSONL; each record has a `line` field

## Notes
- Time parsing is best-effort; if a line doesn’t contain a recognizable timestamp, it is kept to avoid accidental data loss
- Regex filtering still applies after time filtering

