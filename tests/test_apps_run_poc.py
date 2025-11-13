from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from apps.orchestrator import run_poc


class RunPocEntrypointTests(unittest.TestCase):
    """Ensure the thin apps/orchestrator shim forwards the right args."""

    @mock.patch("apps.orchestrator.run_poc._cli_main", return_value=0)
    def test_defaults_forward_to_primary_cli(self, mock_main: mock.Mock) -> None:
        exit_code = run_poc.main([])

        self.assertEqual(exit_code, 0)
        mock_main.assert_called_once()
        forwarded = mock_main.call_args[0][0]

        def _value(flag: str) -> Path:
            idx = forwarded.index(flag)
            return Path(forwarded[idx + 1])

        self.assertEqual(_value("--repo-root"), run_poc.REPO_ROOT)
        self.assertEqual(_value("--config"), run_poc.REPO_ROOT / run_poc.DEFAULT_CONFIG_REL)
        self.assertEqual(
            _value("--constraints"), run_poc.REPO_ROOT / run_poc.DEFAULT_CONSTRAINTS_REL
        )
        self.assertEqual(_value("--output-dir"), run_poc.REPO_ROOT / run_poc.DEFAULT_OUTPUT_REL)
        self.assertEqual(_value("--concept"), run_poc.REPO_ROOT / run_poc.DEFAULT_CONCEPTS_REL)
        self.assertEqual(
            _value("--science-config"), run_poc.REPO_ROOT / run_poc.DEFAULT_SCIENCE_CONFIG_REL
        )

    @mock.patch("apps.orchestrator.run_poc._cli_main", return_value=0)
    def test_overrides_and_flags(self, mock_main: mock.Mock) -> None:
        exit_code = run_poc.main(
            [
                "--constraints",
                "/tmp/constraints.yaml",
                "--concepts",
                "/tmp/concepts",
                "--notebook",
                "demo-notebook",
                "--ablations",
                "no_students",
                "--output-dir",
                "/tmp/outputs",
                "--science-config",
                "./configs/science.yaml",
                "--dry-run",
                "--quiet",
                "--ingest-world-model",
                "--skip-notebook-create",
            ]
        )

        self.assertEqual(exit_code, 0)
        forwarded = mock_main.call_args[0][0]
        self.assertIn("--constraints", forwarded)
        self.assertIn("--concept", forwarded)
        self.assertIn("--notebook", forwarded)
        self.assertIn("--ablations", forwarded)
        self.assertIn("--output-dir", forwarded)
        self.assertIn("--dry-run", forwarded)
        self.assertIn("--quiet", forwarded)
        self.assertIn("--ingest-world-model", forwarded)
        self.assertIn("--skip-notebook-create", forwarded)
        self.assertIn("--science-config", forwarded)

        def _value(flag: str) -> str:
            idx = forwarded.index(flag)
            return forwarded[idx + 1]

        self.assertEqual(Path(_value("--constraints")), Path("/tmp/constraints.yaml").resolve())
        self.assertEqual(Path(_value("--concept")), Path("/tmp/concepts").resolve())
        self.assertEqual(_value("--notebook"), "demo-notebook")
        self.assertEqual(_value("--ablations"), "no_students")
        self.assertEqual(Path(_value("--output-dir")), Path("/tmp/outputs").resolve())
        self.assertEqual(Path(_value("--science-config")), Path("./configs/science.yaml").resolve())

    @mock.patch("apps.orchestrator.run_poc._cli_main", return_value=0)
    def test_repo_root_override_without_explicit_flags(self, mock_main: mock.Mock) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            config_dir = repo_root / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / run_poc.DEFAULT_CONSTRAINTS_REL.name).write_text("title: tmp\n", encoding="utf-8")
            data_dir = repo_root / run_poc.DEFAULT_CONCEPTS_REL
            data_dir.mkdir(parents=True, exist_ok=True)
            exit_code = run_poc.main(["--repo-root", str(repo_root)])

        self.assertEqual(exit_code, 0)
        forwarded = mock_main.call_args[0][0]

        def _path(flag: str) -> Path:
            idx = forwarded.index(flag)
            return Path(forwarded[idx + 1])

        expected_root = repo_root.resolve()
        self.assertEqual(_path("--repo-root"), expected_root)
        self.assertEqual(_path("--config"), expected_root / run_poc.DEFAULT_CONFIG_REL)
        self.assertEqual(_path("--constraints"), expected_root / run_poc.DEFAULT_CONSTRAINTS_REL)
        self.assertEqual(_path("--concept"), expected_root / run_poc.DEFAULT_CONCEPTS_REL)
        self.assertEqual(_path("--output-dir"), expected_root / run_poc.DEFAULT_OUTPUT_REL)
        self.assertNotIn("--science-config", forwarded)

    @mock.patch("apps.orchestrator.run_poc._cli_main", return_value=0)
    def test_repo_root_override_detects_science_config(self, mock_main: mock.Mock) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            config_dir = repo_root / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            constraints_path = config_dir / run_poc.DEFAULT_CONSTRAINTS_REL.name
            constraints_path.write_text("title: tmp\n", encoding="utf-8")
            science_path = config_dir / run_poc.DEFAULT_SCIENCE_CONFIG_REL.name
            science_path.write_text("metrics: {}\n", encoding="utf-8")
            data_dir = repo_root / run_poc.DEFAULT_CONCEPTS_REL
            data_dir.mkdir(parents=True, exist_ok=True)
            exit_code = run_poc.main(["--repo-root", str(repo_root)])

        self.assertEqual(exit_code, 0)
        forwarded = mock_main.call_args[0][0]
        self.assertIn("--science-config", forwarded)

        def _path(flag: str) -> Path:
            idx = forwarded.index(flag)
            return Path(forwarded[idx + 1])

        self.assertEqual(_path("--science-config"), science_path.resolve())

    @mock.patch("apps.orchestrator.run_poc._cli_main", return_value=0)
    def test_relative_paths_anchor_to_repo_root(self, mock_main: mock.Mock) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            exit_code = run_poc.main(
                [
                    "--repo-root",
                    str(repo_root),
                    "--constraints",
                    "config/custom.yaml",
                    "--concepts",
                    "data/handcrafted/custom",
                    "--output-dir",
                    "outputs/smoke",
                    "--config",
                    "config/pipeline-alt.yaml",
                    "--science-config",
                    "config/science-alt.yaml",
                ]
            )

        self.assertEqual(exit_code, 0)
        forwarded = mock_main.call_args[0][0]

        def _path(flag: str) -> Path:
            idx = forwarded.index(flag)
            return Path(forwarded[idx + 1])

        expected_root = repo_root.resolve()
        self.assertEqual(_path("--repo-root"), expected_root)
        self.assertEqual(_path("--constraints"), expected_root / "config" / "custom.yaml")
        self.assertEqual(_path("--concept"), expected_root / "data" / "handcrafted" / "custom")
        self.assertEqual(_path("--output-dir"), expected_root / "outputs" / "smoke")
        self.assertEqual(_path("--config"), expected_root / "config" / "pipeline-alt.yaml")
        self.assertEqual(_path("--science-config"), expected_root / "config" / "science-alt.yaml")

    @mock.patch("apps.orchestrator.run_poc._cli_main", return_value=0)
    def test_skips_constraints_flag_when_default_missing(self, mock_main: mock.Mock) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "config").mkdir(parents=True, exist_ok=True)
            exit_code = run_poc.main(["--repo-root", str(repo_root)])

        self.assertEqual(exit_code, 0)
        forwarded = mock_main.call_args[0][0]
        self.assertNotIn("--constraints", forwarded)

    @mock.patch("apps.orchestrator.run_poc._cli_main", return_value=0)
    def test_skips_concept_flag_when_default_missing(self, mock_main: mock.Mock) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            exit_code = run_poc.main(["--repo-root", str(repo_root)])

        self.assertEqual(exit_code, 0)
        forwarded = mock_main.call_args[0][0]
        self.assertNotIn("--concept", forwarded)

    @mock.patch("apps.orchestrator.run_poc._cli_main", return_value=0)
    def test_skips_science_config_flag_when_default_missing(self, mock_main: mock.Mock) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            config_dir = repo_root / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / run_poc.DEFAULT_CONSTRAINTS_REL.name).write_text("title: tmp\n", encoding="utf-8")
            data_dir = repo_root / run_poc.DEFAULT_CONCEPTS_REL
            data_dir.mkdir(parents=True, exist_ok=True)
            exit_code = run_poc.main(["--repo-root", str(repo_root)])

        self.assertEqual(exit_code, 0)
        forwarded = mock_main.call_args[0][0]
        self.assertNotIn("--science-config", forwarded)

    def test_script_imports_without_repo_root_on_sys_path(self) -> None:
        repo_root = run_poc.REPO_ROOT
        script_path = repo_root / "apps" / "orchestrator" / "run_poc.py"
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.setdefault("OPENAI_API_KEY", "test-key")
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0
        assert "CourseGen pipeline" in result.stdout


if __name__ == "__main__":
    unittest.main()
