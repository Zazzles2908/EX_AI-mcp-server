# CI/Test Hygiene Notes (EX fork)

Some upstream tests target providers intentionally disabled in this EX fork (Gemini/OpenAI/DIAL). If your CI runs the full tests directory, you may get import errors for these optional providers.

Recommended options:

- Skip optional-provider tests via markers or path filters in CI (pytest -k 'not gemini and not openai and not dial', or adjust testpaths)
- Alternatively, guard those tests with environment variables, e.g. only import when PROVIDER_X_ENABLED=true
- Keep KIMI and GLM smoke tests enabled to validate core providers

Example pytest invocation:

```
pytest -q -k "not gemini and not openai and not dial"
```

Or in pytest.ini add custom markers and deselect them in CI.

