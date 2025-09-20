# Git and GitHub on Windows: Copy-Paste Setup Guide

This guide gives you short, copy‑paste friendly steps to configure Git and GitHub CLI (gh) on Windows, fix common token issues, and make pushing to GitHub seamless. It also shows how our gh-mcp server is integrated so AI tools can use GitHub for you.

If any step errors, copy the exact output and ask for help.

---

## 1) Open a terminal
Pick one:
- Start menu → Git Bash
- Start menu → Windows PowerShell
- VS Code → Terminal → New Terminal
- GitHub Desktop → Repository → Open in Command Prompt/PowerShell

All commands below are PowerShell-compatible. If something fails, try in Git Bash.

## 2) Verify installs
```powershell
git --version
gh --version
```

## 3) Set your Git identity (global)
Replace with your name and email:
```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
```
Recommended defaults:
```powershell
git config --global core.autocrlf true
git config --global pull.rebase false
```
Optional (use VS Code editor):
```powershell
git config --global core.editor "code --wait"
```

## 4) Log in to GitHub CLI
This opens your browser:
```powershell
gh auth login --hostname github.com --git-protocol https --web
```
Verify:
```powershell
gh auth status --hostname github.com
```
You should see you are logged in and which protocol is used (https).

## 5) If gh shows a bad GITHUB_TOKEN (common fix)
Symptoms: gh says it is using GITHUB_TOKEN and failing; or you want gh to use the keyring login.

Clear in current session:
```powershell
Remove-Item Env:GITHUB_TOKEN -ErrorAction SilentlyContinue
Remove-Item Env:GH_TOKEN -ErrorAction SilentlyContinue
$env:GITHUB_TOKEN
$env:GH_TOKEN
```
Remove permanently for current user:
```powershell
[Environment]::SetEnvironmentVariable("GITHUB_TOKEN", $null, "User")
[Environment]::SetEnvironmentVariable("GH_TOKEN", $null, "User")
```
Optionally remove machine-wide (run as Admin):
```powershell
Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile -Command "[Environment]::SetEnvironmentVariable(\"GITHUB_TOKEN\", $null, \"Machine\"); [Environment]::SetEnvironmentVariable(\"GH_TOKEN\", $null, \"Machine\")"'
```
Restart the terminal and verify:
```powershell
$env:GITHUB_TOKEN
$env:GH_TOKEN
gh auth status --hostname github.com
```

## 6) Make Git use gh for credentials (seamless HTTPS)
```powershell
gh auth setup-git
```

## 7) Set remote to HTTPS and test access (per repo)
From your repository folder:
```powershell
cd C:\Project\Git_cli
# Replace with your repo URL if different
git remote set-url origin https://github.com/Zazzles2908/Git_cli.git
git remote -v
# Non-destructive access test
git ls-remote --heads origin
```
Expected: you see refs printed, no password prompts.

Optional push test (only if you have commits):
```powershell
git push -u origin main
```

## 8) Troubleshooting quick hits
- Token keeps reappearing: check your PowerShell profile for lines setting GITHUB_TOKEN/GH_TOKEN:
  ```powershell
  $PROFILE
  Test-Path $PROFILE
  if (Test-Path $PROFILE) { Select-String -Path $PROFILE -Pattern 'GITHUB_TOKEN|GH_TOKEN' -SimpleMatch }
  ```
  Remove any such lines, save, restart PowerShell.
- Remote is SSH (git@github.com:...): switch to HTTPS as in section 7.
- Credential popups still appear: rerun `gh auth setup-git`, then `git ls-remote --heads origin` to verify.

---

# gh-mcp: GitHub MCP server integration

We ship a Model Context Protocol (MCP) server that wraps GitHub CLI (gh) so AI tools can perform Git/GitHub operations safely.

## How it is configured
- Server script: `gh-cli/mcp/gh-mcp/dist/server.js`
- MCP config entry (mcp-config.augmentcode.json) includes "gh-mcp" with `transport: stdio` and `command: node`.
- Env: `GH_HOST=github.com` (default). Optional: `AUGGIE_GH_PATH` to point to gh.exe if gh isn’t on PATH.

## Useful gh-mcp tools (selected)
- `gh_bootstrap`: Verify gh presence and auth
- `gh_auth_status`, `gh_api`: Raw GitHub API via gh
- `gh_repo_status`: Show local/origin/remote SHAs and current branch
- `gh_repo_auto_sync`: Stage, optional commit, push, verify
- `gh_repo_set_remote`: Force HTTPS remote
- `gh_repo_credentials_harden`: Configure repo credential helper to gh and verify
- `gh_repo_ensure`, `gh_repo_ensure_auto`: Idempotent repo creation/push
- `gh_pr_list`, `gh_issue_list`, `gh_repo_list`: Convenience listings

## Default repo path for gh tools
- We set `GH_MCP_DEFAULT_REPO_PATH=C:/Project/Git_cli` in `gh-cli/.env` so tools default to this repo when no path is provided.
- You can always override by passing a `targetPath`.

## Safety notes
- Tools avoid storing tokens in files. Prefer `gh auth login` and the system keyring.
- Pre-push check can warn about obvious secret files.
- Operations are idempotent where possible and prefer HTTPS with gh credential helper.

---

If you need help beyond this guide, share the exact command you ran and its output.


## 9) Advanced: hunt down persistent GITHUB_TOKEN
If `gh auth status` still shows an invalid `GITHUB_TOKEN`:

Check all scopes of the variable:
```powershell
'Process:  ' + [Environment]::GetEnvironmentVariable('GITHUB_TOKEN','Process')
'User:     ' + [Environment]::GetEnvironmentVariable('GITHUB_TOKEN','User')
'Machine:  ' + [Environment]::GetEnvironmentVariable('GITHUB_TOKEN','Machine')
'Process:  ' + [Environment]::GetEnvironmentVariable('GH_TOKEN','Process')
'User:     ' + [Environment]::GetEnvironmentVariable('GH_TOKEN','User')
'Machine:  ' + [Environment]::GetEnvironmentVariable('GH_TOKEN','Machine')
```
If User/Machine shows a value, clear it (run last one as Admin for `Machine`):
```powershell
[Environment]::SetEnvironmentVariable('GITHUB_TOKEN', $null, 'User')
[Environment]::SetEnvironmentVariable('GH_TOKEN', $null, 'User')
Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile -Command "[Environment]::SetEnvironmentVariable(\'GITHUB_TOKEN\',$null,\'Machine\');[Environment]::SetEnvironmentVariable(\'GH_TOKEN\',$null,\'Machine\')"'
```

Check PowerShell profiles for token exports:
```powershell
$profiles = @($PROFILE.AllUsersAllHosts, $PROFILE.AllUsersCurrentHost, $PROFILE.CurrentUserAllHosts, $PROFILE.CurrentUserCurrentHost) | Where-Object { $_ -and (Test-Path $_) }
$profiles | ForEach-Object { "--- $_"; Get-Content $_ | Select-String -SimpleMatch 'GITHUB_TOKEN','GH_TOKEN' }
```
Open any file that shows matches and remove the lines, then restart PowerShell.

VS Code integrated terminal env:
- Ctrl+Shift+P → Preferences: Open Settings (JSON)
- Search for `terminal.integrated.env.windows`
- Remove any `GITHUB_TOKEN`/`GH_TOKEN` entries, save, restart VS Code

Windows Terminal:
- Open Settings → Open JSON file
- Search for `GITHUB_TOKEN`/`GH_TOKEN` and remove if present; restart Windows Terminal

After fixes, open a brand-new terminal and verify:
```powershell
$env:GITHUB_TOKEN
$env:GH_TOKEN
gh auth status --hostname github.com
```
