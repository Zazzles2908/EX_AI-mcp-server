# Native provider scaffolds (gated)  Batch 8

Oneliner: YES  Zhipu (GLM) and Moonshot (Kimi) native scaffolds exist; pycompile successful; not wired by default.

## Actions
- Verified src/providers/zhipu_native.py and src/providers/moonshot_native.py present
- Compiled: `python -m py_compile src/providers/zhipu_native.py src/providers/moonshot_native.py`  exit 0
- No wiring or network calls added (gated; safe)

## Notes
- Future steps may add example requests under flags and providerspecific adapters; keep scaffolds importsafe.

