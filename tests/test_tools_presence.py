import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from server import TOOLS

def test_required_tools_present():
    required = {
        "consensus",
        "orchestrate_auto",
        "kimi_chat_with_tools",
        "kimi_upload_and_extract",
        "secaudit",
        "testgen",
        "activity",
        "version",
        "listmodels",
        "provider_capabilities",
        "health",
        "browse_orchestrator",
    }
    names = set(TOOLS.keys())
    missing = sorted(list(required - names))
    assert not missing, f"Missing tools: {missing}"

