# Contributing to EX MCP Server

Thank you for your interest in contributing! This project follows clear quality and testing standards to keep releases stable and useful for the community.

- Start with docs/contributions.md for the full guide
- Run code quality checks locally before opening a PR
- Add tests for new features and bug fixes

## Quick Start (Development)

1. Clone and set up environment
```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

2. Configure environment
```
cp .env.example .env
# Set at least one provider (KIMI_API_KEY, GLM_API_KEY, OPENROUTER_API_KEY, or CUSTOM_API_URL)
```

3. Run the server locally
```
python -m server  # or: python server.py
```

4. Run quality checks
```
ruff check . --fix
black .
isort .
pytest -xvs
```

## Pull Requests

- Use conventional commit-style prefixes in PR titles: feat:, fix:, docs:, chore:, test:, refactor:, perf:
- Ensure all checks pass 100% (lint + tests) before requesting review
- Update documentation when behavior changes

For in-depth details (testing strategy, simulator tests, PR checklist), see docs/contributions.md.

