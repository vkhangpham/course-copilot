from pathlib import Path
from unittest import mock

from pytest import MonkeyPatch

from apps.orchestrator import run_poc
from apps.orchestrator.run_poc import build_parser


def test_parser_accepts_concept_alias() -> None:
    parser = build_parser()
    namespace = parser.parse_args(["--concept", "/tmp/concepts"])
    assert namespace.concepts == "/tmp/concepts"


def test_parser_accepts_concepts_flag() -> None:
    parser = build_parser()
    namespace = parser.parse_args(["--concepts", "/tmp/other"])
    assert namespace.concepts == "/tmp/other"


@mock.patch("apps.orchestrator.run_poc._cli_main", return_value=0)
def test_dataset_env_override_preempts_default(
    mock_main: mock.Mock, tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "data" / "handcrafted" / "database_systems").mkdir(parents=True)
    env_dataset = tmp_path / "env_dataset"
    env_dataset.mkdir()
    monkeypatch.setenv("COURSEGEN_DATASET_DIR", str(env_dataset))

    exit_code = run_poc.main(["--repo-root", str(repo_root)])

    assert exit_code == 0
    forwarded: list[str] = mock_main.call_args[0][0]
    path = Path(forwarded[forwarded.index("--concept") + 1])
    assert path == env_dataset.resolve()


@mock.patch("apps.orchestrator.run_poc._cli_main", return_value=0)
def test_concepts_flag_overrides_env(
    mock_main: mock.Mock, tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    flag_dataset = tmp_path / "forced_dataset"
    flag_dataset.mkdir()
    env_dataset = tmp_path / "env_dataset"
    env_dataset.mkdir()
    monkeypatch.setenv("COURSEGEN_DATASET_DIR", str(env_dataset))

    exit_code = run_poc.main(
        [
            "--repo-root",
            str(repo_root),
            "--concepts",
            str(flag_dataset),
        ]
    )

    assert exit_code == 0
    forwarded: list[str] = mock_main.call_args[0][0]
    path = Path(forwarded[forwarded.index("--concept") + 1])
    assert path == flag_dataset.resolve()
