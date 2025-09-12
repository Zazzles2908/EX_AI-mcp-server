# Git and GitHub: A Practical Guide

This guide explains Git and GitHub concepts and how this project’s automation (gh-mcp and EXAI tools) manages them for you. It’s written to help you understand what happens behind the scenes when the tools operate on your behalf.

## 1) Core Concepts

- Repository (repo): A project folder tracked by Git. It contains your files and a hidden `.git` directory with history and configuration.
- Commit: A snapshot of your repo at a point in time, with a message and a unique SHA (e.g., `a1b2c3...`).
- Branch: A movable pointer to a series of commits. `main` is typically the default branch.
- Remote: A server-side version of your repo (e.g., GitHub). `origin` is the default remote name.
- Push / Pull:
  - Push sends your local commits to the remote.
  - Pull fetches remote commits and merges (or replays) them locally.

## 2) Everyday Git Usage

- Initialize or clone
  - `git init -b main` — start a new repo locally
  - `git clone <url>` — copy an existing remote repo locally
- Make changes and commit
  - `git status` — see changes
  - `git add -A` — stage all modified/new files
  - `git commit -m "message"` — record a snapshot
- Work with remotes
  - `git remote -v` — list remotes
  - `git push origin main` — push local main to GitHub
  - `git pull --rebase origin main` — update local main from GitHub (linear history)
- Branches
  - `git checkout -b feature/x` — create and switch to a new branch
  - `git switch main` — switch back to main
  - `git merge feature/x` — merge changes into the current branch

## 3) Effective Git/GitHub Practices

- Commit early and often; use meaningful messages.
- Keep `main` deployable; use feature branches and PRs for changes.
- Rebase small feature branches before pushing to keep history clean.
- Use `.gitignore` to exclude logs, build artifacts, credentials, and large or generated files.
- Protect `main` on GitHub (required reviews, disallow force-push, require status checks).
- Automate: use scripts and tools (like gh-mcp/EXAI) for repeatable, non-error-prone flows.

## 4) Common Workflows

- Feature flow (recommended)
  1. Create branch: `git checkout -b feature/my-change`
  2. Commit locally: `git add -A && git commit -m "feat: ..."`
  3. Push branch: `git push -u origin feature/my-change`
  4. Open PR on GitHub, get review, merge into `main`

- Hotfix on main (minimal)
  1. Switch to main, pull latest: `git switch main && git pull --rebase`
  2. Fix and commit: `git add -A && git commit -m "fix: ..."`
  3. Push: `git push origin main`

## 5) How this Project Automates Things

- gh-mcp server (GitHub CLI via MCP)
  - Wraps `gh` to perform GitHub actions programmatically.
  - Tools include:
    - `gh_api` — low-level GitHub REST calls (headers/hostname supported)
    - `gh_repo_ensure_auto` / `gh_repo_ensure` — create/connect/push a repo
    - `gh_repo_protect` — apply minimal, safe branch protection (now with `dryRun`)
    - `gh_pre_push_check` — quick local safety checks before pushing
    - `gh_auth_status` — verify auth/host

- EXAI tools
  - `thinkdeep`, `codereview`, `secaudit`, `precommit` and others can:
    - Review code/changes, identify issues, and propose fixes
    - Validate repo state before pushing
    - Generate documentation/tests and suggest security improvements

- Configuration
  - `GH_HOST` controls the GitHub host (e.g., `github.com` or GHE). The server now defaults to `GH_HOST` when hostname isn’t provided.
  - Default headers include `Accept: application/vnd.github+json` and `X-GitHub-Api-Version: 2022-11-28`.

## 6) Behind the Scenes (What Happens on Push)

1. Local changes are staged and committed (`git add`, `git commit`).
2. The local branch (e.g., `main`) is pushed (`git push origin main`).
3. GitHub receives the commits; branch protection (if enabled) enforces rules.
4. Tools can verify via GitHub API that the latest commit on GitHub matches local HEAD.

## 7) Troubleshooting Common Issues

- Remote rejected (non-fast-forward)
  - Cause: Remote has new commits you don’t have.
  - Fix: `git pull --rebase origin main`, resolve conflicts, then `git push`.

- Wrong host / API errors
  - Check `GH_HOST` and auth: `gh auth status`
  - Ensure headers are versioned; with gh-mcp, defaults are handled for you.

- Large files or secrets accidentally committed
  - Add to `.gitignore`. For secrets, rotate immediately and remove from history if public.
  - Consider `git filter-repo` (advanced) to rewrite history if necessary.

- Embedded submodules accidentally added
  - You’ll see a 160000 mode entry.
  - Fix: `git rm --cached <path>` then add files normally; or use `git submodule add` if intended.

- Logs keep showing up in `git status`
  - Add patterns to `.gitignore` (e.g., `.logs/*.jsonl`).

## 8) Verifying Local vs Remote (Quick Recipe)

- Local HEAD: `git rev-parse HEAD`
- Remote main (cached): `git rev-parse origin/main`
- Remote main (GitHub): `gh api /repos/<owner>/<repo>/branches/main` and read `.commit.sha`
- They should all match. If not:
  - `git fetch origin`
  - If you’re ahead: `git push origin main`
  - If you’re behind: `git pull --rebase origin main`

## 9) Safe Automation Patterns

- Always run non-destructive dry-runs before applying changes (e.g., `gh_repo_protect` with `dryRun: true`).
- Validate auth/host before doing anything (`gh_auth_status`).
- Prefer smallest, focused operations (single branch, single repo) and verify after each step.

## 10) Quick Command Reference

- Init: `git init -b main`
- Status: `git status -sb`
- Stage/Commit: `git add -A && git commit -m "msg"`
- Branch: `git checkout -b feature/x`
- Push: `git push -u origin feature/x`
- Update: `git pull --rebase origin main`
- Verify remote head: `gh api /repos/<owner>/<repo>/branches/main`

---

If you’re using the automated tools (gh-mcp + EXAI), most of this is handled for you. This guide helps you understand the underlying actions, so you can confidently review and approve them.

