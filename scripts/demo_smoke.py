"""Run the CourseGen PoC demo sequence end-to-end for smoke testing.

Combines the ingest script + orchestrator CLI + artifact verification so CI or
humans can issue a single command when prepping the demo.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from scripts.ingest_handcrafted import ingest  # noqa: E402


def _resolve_path(value: Path | str, base: Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (base / candidate).resolve()


def _latest_manifest(artifacts_dir: Path) -> Tuple[str, Path, Dict[str, Any]]:
    manifests = sorted(artifacts_dir.glob("run-*-manifest.json"))
    if not manifests:
        raise RuntimeError(f"No manifests found in {artifacts_dir}")
    latest = manifests[-1]
    with latest.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    run_id = latest.stem.replace("-manifest", "")
    return run_id, latest, data


def _expect_file(path_value: str | None, repo_root: Path, label: str) -> Path:
    if not path_value:
        raise RuntimeError(f"Manifest missing {label} path")
    path = Path(path_value)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    if not path.exists():
        raise RuntimeError(f"Expected {label} at {path} but it was not found")
    return path


def _run_cli(
    *,
    repo_root: Path,
    constraints: Path | None,
    concepts: Path | None,
    notebook: str,
    ablations: str | None,
    offline_teacher: bool,
) -> None:
    cli_path = repo_root / "apps" / "orchestrator" / "run_poc.py"
    cmd = [
        sys.executable,
        str(cli_path),
        "--repo-root",
        str(repo_root),
        "--notebook",
        notebook,
    ]
    if constraints:
        cmd.extend(["--constraints", str(constraints)])
    if concepts:
        cmd.extend(["--concepts", str(concepts)])
    if ablations:
        cmd.extend(["--ablations", ablations])
    if offline_teacher:
        cmd.append("--offline-teacher")

    env = os.environ.copy()
    if offline_teacher:
        env.setdefault("COURSEGEN_RLM_OFFLINE", "1")

    subprocess.run(cmd, cwd=repo_root, env=env, check=True)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run ingest + CLI + artifact checks for the demo.")
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT, help="Repository root (defaults to script location).")
    parser.add_argument(
        "--concepts",
        type=Path,
        default=Path("data/handcrafted/database_systems"),
        help="Handcrafted dataset directory.",
    )
    parser.add_argument(
        "--constraints",
        type=Path,
        default=Path("config/course_config.yaml"),
        help="Constraints YAML file.",
    )
    parser.add_argument(
        "--notebook",
        default="database-systems-poc",
        help="Notebook slug to target during the run.",
    )
    parser.add_argument(
        "--world-model",
        type=Path,
        default=Path("outputs/world_model/state.sqlite"),
        help="World-model SQLite destination.",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=Path("outputs/world_model/snapshot.jsonl"),
        help="Optional JSONL snapshot output.",
    )
    parser.add_argument("--skip-ingest", action="store_true", help="Reuse existing world-model snapshot.")
    parser.add_argument("--offline-teacher", action="store_true", help="Force the teacher loop into offline mode.")
    parser.add_argument("--ablations", default=None, help="Comma-separated ablation list forwarded to the CLI.")
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    concepts = _resolve_path(args.concepts, repo_root)
    world_model_path = _resolve_path(args.world_model, repo_root)
    snapshot_path = _resolve_path(args.snapshot, repo_root)
    constraints = _resolve_path(args.constraints, repo_root)

    if not args.skip_ingest:
        summary = ingest(concepts, world_model_path, jsonl_path=snapshot_path)
        print(f"[demo] Ingest complete: {summary}")
    else:
        print("[demo] Skipping ingest (reuse existing world-model snapshot)")

    _run_cli(
        repo_root=repo_root,
        constraints=constraints,
        concepts=concepts,
        notebook=args.notebook,
        ablations=args.ablations,
        offline_teacher=args.offline_teacher,
    )

    artifacts_dir = repo_root / "outputs" / "artifacts"
    run_id, manifest_path, manifest = _latest_manifest(artifacts_dir)
    print(f"[demo] Latest run: {run_id} ({manifest_path})")

    course_plan = _expect_file(manifest.get("course_plan"), repo_root, "course_plan")
    lecture = _expect_file(manifest.get("lecture"), repo_root, "lecture")
    eval_report = _expect_file(manifest.get("eval_report"), repo_root, "eval_report")
    _expect_file(manifest.get("world_model_highlight_artifact"), repo_root, "highlight artifact")
    if manifest.get("scientific_metrics_artifact"):
        _expect_file(manifest["scientific_metrics_artifact"], repo_root, "scientific metrics artifact")
    evaluation = manifest.get("evaluation") or {}
    use_students = evaluation.get("use_students", True)
    if use_students and evaluation.get("overall_score") is None:
        raise RuntimeError("Evaluation payload missing overall_score")
    if use_students and not evaluation.get("rubrics"):
        raise RuntimeError("Evaluation payload missing rubric results")

    print("[demo] Artifacts verified:")
    for label, path in (
        ("course plan", course_plan),
        ("lecture", lecture),
        ("evaluation report", eval_report),
    ):
        print(f"  - {label}: {path}")
    print("[demo] Smoke test completed successfully")


if __name__ == "__main__":
    main()
