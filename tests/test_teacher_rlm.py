import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from agents.teacher_rlm import TeacherRLM

_ENV_VAR = "COURSEGEN_VENDOR_RLM_PATH"


class TeacherRLMVendorPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.teacher = TeacherRLM()
        self._sys_path_snapshot = list(sys.path)
        self.addCleanup(self._restore_sys_path)
        self.addCleanup(self._clear_env_override)

    def _restore_sys_path(self) -> None:
        sys.path[:] = self._sys_path_snapshot

    def _clear_env_override(self) -> None:
        os.environ.pop(_ENV_VAR, None)

    def test_vendor_path_defaults_to_rlm_directory(self) -> None:
        os.environ.pop(_ENV_VAR, None)
        expected = Path(__file__).resolve().parents[1] / "vendor" / "rlm"
        self.assertEqual(self.teacher._vendor_rlm_path(), expected)

    def test_vendor_path_respects_env_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ[_ENV_VAR] = tmpdir
            path = self.teacher._vendor_rlm_path()
            self.assertEqual(path, Path(tmpdir))

    def test_resolve_repl_imports_from_vendor_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ[_ENV_VAR] = tmpdir
            vendor_path = Path(tmpdir)
            sentinel = object()
            dummy_module = types.SimpleNamespace(RLM_REPL=lambda: sentinel)
            with mock.patch("importlib.import_module", return_value=dummy_module) as mock_import:
                repl = self.teacher._resolve_repl()
            self.assertIs(repl, sentinel)
            self.assertIn(str(vendor_path), sys.path)
            mock_import.assert_called_once_with("rlm.rlm_repl")


if __name__ == "__main__":
    unittest.main()
