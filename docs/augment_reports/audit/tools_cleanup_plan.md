# Tools Cleanup Plan (Phase C)

Goal: Keep tools/ canonical; remove ghost src/tools/

Current state
- tools/ contains complete implementations
- src/tools/ is a ghost placeholder (no source modules)

Plan
1) Verify no imports reference src.tools
2) If none found, delete src/tools/ directory
3) Add docs/tools/*.md links into augment_reports index for discoverability
4) Ensure server.list_tools builds from tools.registry or static list consistently

Validation
- Grep for `from src.tools` and `import src.tools`
- Run listtools tool; verify expected catalog

