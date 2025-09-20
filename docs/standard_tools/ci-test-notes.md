# CI/Test Hygiene Notes (EX fork)

Some upstream tests target providers intentionally disabled in this EX fork (Gemini/OpenAI/DIAL). If your CI runs the full tests directory, you may get import errors for these optional providers.

Recommended options:

- Prefer deselecting optional-provider tests via markers: use -m "not optional_provider" (see pytest.ini). You can also use path filters (pytest -k 'not gemini and not openai and not dial') if markers are not available.
- Alternatively, guard those tests with environment variables, e.g. only import when PROVIDER_X_ENABLED=true
- Keep KIMI and GLM smoke tests enabled to validate core providers

Example pytest invocation:

```
pytest -q -m "not optional_provider"
# or, if you have not added the marker yet
pytest -q -k "not gemini and not openai and not dial"
```

Or in pytest.ini add custom markers and deselect them in CI.

