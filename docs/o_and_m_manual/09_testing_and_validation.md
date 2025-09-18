# Testing & Validation

## Quality checks (one command)
```
./scripts/code_quality_checks.sh
```
Runs: ruff (fix), black, isort, unit tests (no integration)

## Unit tests
Purpose: validate tool logic and helpers
```
python -m pytest tests/ -v -m "not integration"
```
Run a single test/file:
```
python -m pytest tests/test_refactor.py::TestRefactorTool::test_format_response -v
```

## Integration tests (free local models via Ollama)
Purpose: validate real provider calls against a local endpoint
```
ollama serve
ollama pull llama3.2
# macOS/Linux
export CUSTOM_API_URL="http://localhost:11434"
# Windows PowerShell
$env:CUSTOM_API_URL="http://localhost:11434"
python -m pytest tests/ -v -m "integration"
```

## Simulator tests
Purpose: end-to-end conversation flows with tool orchestration
Quick mode:
```
python communication_simulator_test.py --quick
```
Individual tests:
```
python communication_simulator_test.py --individual basic_conversation
```

## Smoke / ops validations
```
python tools/ws_daemon_smoke.py
```
Expect: stream_demo fallback+stream, thinkdeep web-cue, chat_longcontext activity

