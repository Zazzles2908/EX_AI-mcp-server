import os
from pathlib import Path

import pytest

from src.core.validation.secure_input_validator import SecureInputValidator


@pytest.mark.parametrize(
    "repo_root, external_prefix, target_path, allowed",
    [
        (
            # Repo root is the current EX-AI-MCP-Server
            str(Path.cwd()),
            # Allowlist a sibling/external project
            r"C:/Project/Personal_AI_Agent",
            r"C:/Project/Personal_AI_Agent/some/file.txt",
            True,
        ),
        (
            str(Path.cwd()),
            r"C:/Other/Project",
            r"C:/Project/Personal_AI_Agent/some/file.txt",
            False,
        ),
    ],
)
def test_secure_input_validator_external_allowlist(repo_root, external_prefix, target_path, allowed, monkeypatch):
    # Ensure flags are read from environment
    monkeypatch.setenv("EX_ALLOW_EXTERNAL_PATHS", "true")
    monkeypatch.setenv("EX_ALLOWED_EXTERNAL_PREFIXES", external_prefix)

    v = SecureInputValidator(repo_root=repo_root)
    p = Path(target_path)

    if allowed:
        # Should not raise and should return a resolved Path
        result = v.normalize_and_check(target_path)
        assert isinstance(result, Path)
        assert str(result).startswith(external_prefix)
    else:
        with pytest.raises(ValueError) as ei:
            _ = v.normalize_and_check(target_path)
        assert "escapes repository root" in str(ei.value)

