## Fix guide: Tool-call and progress visibility (VS Code + Auggie CLI)

This guide explains why you’re not seeing per-step tool calls in the UI and how to make them visible across both VS Code and the Auggie CLI. It’s based on your current default VS Code settings snapshot and the EX MCP Server code.

---

### Symptoms
- VS Code chat session doesn’t show per-step tool call dropdowns/progress.
- Auggie CLI doesn’t visibly show which tools were called.

### Quick root-cause summary
1) MCP stdio hides most live logs from clients during tool execution. EX MCP writes visibility signals to local log files instead (design):
   - logs/mcp_server.log (everything)
   - logs/mcp_activity.log (tool-call breadcrumbs: TOOL_CALL, TOOL_COMPLETED, [PROGRESS] …)
2) If activity logging or streaming is disabled, UI will appear silent.
3) VS Code’s defaults have MCP enabled, but autostart is set to "never"; if your client doesn’t explicitly start the server, you won’t see any events.
4) Auggie CLI can surface progress inline via the aug_* wrappers, but wrappers activate only when AUGGIE_CLI=true and ALLOW_AUGGIE=true are present in the server process environment, and the CLI targets aug_* tools (or you read the activity log).
5) When Auggie wrappers output is set to compact JSON, progress exists but is less visible unless you expand the JSON; you can switch to pretty text with wrappers.compact_output=false.

---

## Checklist: Make tool calls visible fast
Do these first; they’re safe and reversible.

1) Environment (.env)
- STREAM_PROGRESS=true
- ACTIVITY_LOG=true
- LOG_LEVEL=INFO
- LOG_FORMAT=plain (easier to read while debugging)
- Optional: EX_TOOLCALL_LOG_PATH=.logs/toolcalls.jsonl (JSONL mirror)

2) Ensure the activity log file exists and is populated
- After running any tool, confirm: logs/mcp_activity.log contains lines like TOOL_CALL, TOOL_COMPLETED, [PROGRESS].
- If the Activity tool returns “Log file not found,” start a tool once (e.g., listmodels) to force creation, or verify ACTIVITY_LOG=true.

3) VS Code client settings (your snapshot looks fine for enablement)
- Confirm MCP is enabled and discovery is on (your defaults already are):
  - chat.mcp.enabled = true
  - chat.mcp.discovery.enabled = true
- Optional QoL: autostart new servers so you don’t forget to start the EX server:
  - chat.mcp.autostart = "newAndOutdated" (instead of "never")
- Where to look during a run:
  - View → Output → select the extension’s channel and/or EX MCP activity channel.
  - If UI doesn’t show per-step dropdowns, open the logs directly: logs/mcp_activity.log.

4) Auggie CLI configuration (to display progress inline)
- Use auggie-config.json (next to server) and add environment + wrapper prefs:

{
  "mcpServers": {
    "ex": {
      "command": "python",
      "args": ["<ABSOLUTE_PATH>/scripts/mcp_server_wrapper.py"],
      "cwd": "<ABSOLUTE_PATH>",
      "env": {
        "PYTHONPATH": "<ABSOLUTE_PATH>",
        "AUGGIE_CLI": "true",
        "ALLOW_AUGGIE": "true",
        "STREAM_PROGRESS": "true",
        "ACTIVITY_LOG": "true",
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "plain"
      }
    }
  },
  "auggie": {
    "wrappers": {
      "show_progress": true,
      "compact_output": false  
    }
  }
}

- Why:
  - AUGGIE_CLI + ALLOW_AUGGIE activate aug_* wrappers that embed progress in CLI output.
  - compact_output=false prints readable progress bullets instead of a single compact JSON line.
- Run Auggie with the config:
  - auggie --mcp-config <ABSOLUTE_PATH>/auggie-config.json

5) Verify with the built-in Activity tool
- From the EX tools: run the activity tool with a filter to see just the relevant lines:
  - filter: "TOOL_CALL|TOOL_COMPLETED|PROGRESS"
  - lines: 300 (as needed)
- If it errors with "Log file not found": set EX_ACTIVITY_LOG_PATH to your actual activity file if customized, else ensure logs/mcp_activity.log exists.

---

## What your VS Code defaults tell us
From tests/vsc_settings/currentdefault_settings.json:
- chat.mcp.enabled = true (good)
- chat.mcp.discovery.enabled = true (good)
- chat.mcp.autostart = "never" (you must start servers manually; change to "newAndOutdated" for convenience)
- No setting here will hide tool calls if the server emits them; visibility gating happens in env + client UI + log availability.

---

## How EX MCP emits visibility
- Server writes rotating logs under logs/ (created automatically):
  - logs/mcp_server.log → master log
  - logs/mcp_activity.log → activity breadcrumbs (TOOL_CALL, TOOL_COMPLETED, TOOL_SUMMARY, [PROGRESS] …)
- Controls:
  - ACTIVITY_LOG=true enables activity logger
  - STREAM_PROGRESS=true causes tools to send [PROGRESS] messages via a centralized helper that logs to mcp_activity
  - EX_ACTIVITY_LOG_PATH overrides the path that the Activity tool reads (defaults to logs/mcp_activity.log)
- Auggie wrappers (aug_chat, aug_thinkdeep, aug_consensus) can inline progress into CLI output when enabled.

---

## Step-by-step: end-to-end validation
1) Start the server once (VS Code or CLI) and run a small tool, e.g., listmodels or version.
2) Tail your activity log:
   - PowerShell: Get-Content logs\mcp_activity.log -Wait -Tail 50
   - Expect lines: TOOL_CALL: version …, [PROGRESS] …, TOOL_COMPLETED: version …
3) Use the Activity tool to view the last 200 lines with a filter:
   - filter: TOOL_CALL|TOOL_COMPLETED|PROGRESS
4) In Auggie CLI, run a tool via wrappers (e.g., aug_thinkdeep) and check inline output contains a Progress section. If not, re-check AUGGIE_CLI/ALLOW_AUGGIE env and wrappers.compact_output.
5) Optional JSONL mirror: check .logs/toolcalls.jsonl for sanitized tool call events if EX_TOOLCALL_LOG_PATH is set.

---

## Common pitfalls and fixes
- Activity tool returns error: "Log file not found or inaccessible":
  - Ensure ACTIVITY_LOG=true and that at least one tool has run (to create the file).
  - Confirm the file path is logs/mcp_activity.log or set EX_ACTIVITY_LOG_PATH to the right path.
- VS Code shows nothing during tool run:
  - This is expected for many clients due to stdio; use the Output panel and/or logs/mcp_activity.log.
  - Make sure the EX server actually started (consider setting chat.mcp.autostart to newAndOutdated).
- Auggie CLI doesn’t show progress inline:
  - Ensure auggie-config.json passes AUGGIE_CLI=true and ALLOW_AUGGIE=true to the server.
  - Ensure wrappers.compact_output=false for readable text output.
  - If you are calling “chat” instead of “aug_chat”, rely on the activity log or invoke the aug_* tool names.
- No progress lines appear:
  - Verify STREAM_PROGRESS=true and LOG_LEVEL=INFO.
  - Some tools emit minimal progress; try thinkdeep/analyze which produce more checkpoints.
- Permissions/paths on Windows:
  - Keep paths absolute in auggie-config.json.
  - Ensure logs/ directory is writable by your user.

---

## Minimal test commands (safe)
- View last 200 lines of activity with filter:
  - PowerShell: Select-String -Path logs\mcp_activity.log -Pattern "TOOL_CALL|TOOL_COMPLETED|PROGRESS" | Select-Object -Last 200
- Run the quick demo that emits progress (requires Python env):
  - python scripts/show_progress_json.py
- E2E lightweight check (if pytest available):
  - pytest -q tests/test_e2e_exai_ultimate.py::test_tool_call_visibility_logs

---

## If problems persist
Share: logs/mcp_server.log and logs/mcp_activity.log around the time of a run, and your auggie-config.json (with keys redacted). We’ll help pinpoint whether env variables aren’t reaching the server process or a path mismatch prevents reading the activity log.

