import os
import sys
import pytest
from pathlib import Path

from src.core.validation.secure_input_validator import SecureInputValidator


@pytest.mark.skipif(sys.platform != "win32", reason="Windows path variants tested on win32 only")
class TestSecureInputValidatorWindowsVariants:
    def setup_method(self):
        # Use repo root as current working directory
        self.repo_root = Path(os.getcwd()).resolve()
        self.v = SecureInputValidator(repo_root=str(self.repo_root))

    def test_absolute_drive_path_outside_repo_rejected(self):
        # Pick a path on C: that is unlikely to be in repo root
        abs_path = Path("C:/Windows/System32/drivers/etc/hosts")
        with pytest.raises(ValueError):
            self.v.normalize_and_check(str(abs_path))

    def test_unc_path_outside_repo_rejected(self):
        unc = r"\\SomeServer\SomeShare\file.txt"
        with pytest.raises(ValueError):
            self.v.normalize_and_check(unc)

    def test_allowlist_env_enables_external_path(self, monkeypatch):
        abs_path = Path("C:/Temp/test.txt").resolve()
        monkeypatch.setenv("EX_ALLOW_EXTERNAL_PATHS", "true")
        monkeypatch.setenv("EX_ALLOWED_EXTERNAL_PREFIXES", str(abs_path.parent))
        v2 = SecureInputValidator(repo_root=str(self.repo_root))
        p = v2.normalize_and_check(str(abs_path))
        assert str(p).startswith(str(abs_path.parent))

