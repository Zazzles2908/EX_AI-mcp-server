import os
from pathlib import Path

print("[SMOKE] Starting router/validator checks")

# Enable router for this run
os.environ["ROUTER_ENABLED"] = "true"

# ModelRouter checks
try:
    from utils.model_router import ModelRouter, RoutingContext
    print("[SMOKE] ModelRouter import: OK")
    print("[SMOKE] Router enabled:", ModelRouter.is_enabled())
    r1 = ModelRouter.decide(RoutingContext(tool_name="chat", prompt="hi", files_count=0, images_count=0, requested_model="auto"))
    r2 = ModelRouter.decide(RoutingContext(tool_name="secaudit", prompt="security audit on auth", files_count=1, images_count=0, requested_model="auto"))
    r3 = ModelRouter.decide(RoutingContext(tool_name="chat", prompt="include image", files_count=0, images_count=1, requested_model="auto"))
    print("[SMOKE] chat->", r1)
    print("[SMOKE] secaudit->", r2)
    print("[SMOKE] vision->", r3)
except Exception as e:
    print("[SMOKE] ModelRouter error:", type(e).__name__, e)

# SecureInputValidator checks
try:
    from src.core.validation.secure_input_validator import SecureInputValidator
    root = Path('.').resolve()
    v = SecureInputValidator(repo_root=str(root))
    candidate = "README.md" if (root/"README.md").exists() else ".gitignore"
    p = v.normalize_and_check(candidate)
    print("[SMOKE] Validator import/normalize: OK ->", p)
except Exception as e:
    print("[SMOKE] Validator error:", type(e).__name__, e)

