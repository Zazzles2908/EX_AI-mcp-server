# Make EX MCP global in VS Code (Augment)

This guide registers the EX MCP server once (User Settings), so every project can use it without copying settings into each repo.

## Prerequisites
- VS Code with the Augment extension installed/updated
- This repo cloned locally (path in examples below)
- API keys (optional but recommended): KIMI_API_KEY and/or GLM_API_KEY; optionally OPENROUTER_API_KEY or CUSTOM_API_URL

## 1) Open VS Code User Settings (JSON)
- Command Palette → “Preferences: Open User Settings (JSON)”
- You’ll edit your global settings.json (not the workspace .vscode/settings.json)

## 2) Add the global EX MCP server entry
Pick ONE of the two options.

Option A — use the console script if installed (ex-mcp-server on PATH):

```
{
  "chat.mcp.discovery.enabled": true,
  "chat.mcp.autostart": "whenUsed",   // or "always"
  "chat.mcp.servers": {
    "ex-mcp": {
      "transport": "stdio",
      "command": "ex-mcp-server",
      "args": [],
      "env": {
        "DEFAULT_MODEL": "glm-4.5-flash"
      }
    }
  }
}
```

Option B — call Python directly (no console script):

```
{
  "chat.mcp.discovery.enabled": true,
  "chat.mcp.autostart": "whenUsed",
  "chat.mcp.servers": {
    "ex-mcp": {
      "transport": "stdio",
      "command": "python",
      "args": [
        "c:/Project/EX-AI-MCP-Server/server.py"
      ],
      "env": {
        "DEFAULT_MODEL": "glm-4.5-flash"
      }
    }
  }
}
```

Notes
- Keep only one ex-mcp block. If you already have a chat.mcp.servers object, merge entries.
- You can switch DEFAULT_MODEL to "auto" to let the server choose per tool.

## 3) Set provider environment variables (Windows)
Open PowerShell and set any you plan to use, then restart VS Code:

```
setx KIMI_API_KEY "<your_key>"
setx GLM_API_KEY "<your_key>"
:: Optional
setx OPENROUTER_API_KEY "<your_key>"
setx CUSTOM_API_URL "http://localhost:11434"  
setx CUSTOM_MODEL_NAME "llama3.2"
```

Optional visibility helper (we already enabled a server fallback, but you can set this too):
```
setx INLINE_PROGRESS_IN_TEXT true
```

## 4) Restart VS Code and verify
- View → Output → pick “Augment” or “Augment Agent”
- You should see lines like: “MCP Client Connected: ex-server” and tool discovery
- In chat, run: listmodels_exai — you should see the models list with a PROGRESS block at the top

## 5) Use in any project
Once the User Settings entry exists, every workspace can use EX MCP without any per-project config.

### If a workspace has its own .vscode/settings.json
- It can override or add servers, but it is not required
- Remove duplicated ex-mcp definitions in repos to avoid confusion; rely on the User Settings one

## 6) Optional: Autostart
- "chat.mcp.autostart": "whenUsed" starts EX MCP when a message triggers it
- Set to "always" to start it on session open (slightly faster first call)

## 7) Troubleshooting
- No dropdown? The UI may not render metadata yet. We inline the PROGRESS block into the primary text, so you should still see steps.
- No models found? Run listmodels_exai and check the Output panel for which API keys are detected.
- Command not found? Use Option B (python + server.py path) or ensure ex-mcp-server is on PATH.
- Windows quoting: use forward slashes or double-escape backslashes in JSON if needed.

## 8) Per-workspace override (only if you want it)
Create .vscode/settings.json inside a repo with the same server block to pin a different DEFAULT_MODEL or env just for that project. Otherwise, rely on the global entry.

## 9) What “global” gives you
- One place to maintain MCP servers and defaults
- All projects share the same EX MCP configuration and progress visibility
- You can still override per-project when needed

