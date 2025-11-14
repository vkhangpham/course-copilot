"""Bootstrap helpers for the CourseGen pipeline."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict

import yaml
from dotenv import load_dotenv

from ccopilot.core.ablation import AblationConfig, parse_ablation_flag
from ccopilot.core.config import PipelineConfig, load_course_constraints, load_pipeline_config
from ccopilot.core.dspy_runtime import DSPyConfigurationError, configure_dspy_models
from ccopilot.core.provenance import ProvenanceEvent, ProvenanceLogger
from scripts import ingest_handcrafted

from .context import PipelineContext, PipelinePaths

DEFAULT_CONFIG_PATH = Path("config/pipeline.yaml")
DEFAULT_OUTPUT_DIR = Path("outputs")
LOGGER = logging.getLogger(__name__)


def _capture_env(keys: tuple[str, ...]) -> Dict[str, str]:
    """Return a filtered snapshot of environment variables for provenance."""
    snapshot: Dict[str, str] = {}
    for key in keys:
        value = os.getenv(key)
        if value is not None:
            snapshot[key] = value
    return snapshot


def bootstrap_pipeline(
    config_path: Path | None = None,
    *,
    repo_root: Path | None = None,
    output_dir: Path | None = None,
    ablations: str | None = None,
    env_keys: tuple[str, ...] = ("OPENAI_API_KEY", "OPEN_NOTEBOOK_API_BASE", "OPEN_NOTEBOOK_SLUG"),
    dataset_dir_override: Path | None = None,
    world_model_store_override: Path | None = None,
    ingest_before_run: bool = False,
    constraints_path: Path | None = None,
    notebook_slug_override: str | None = None,
    notebook_auto_create_override: bool | None = None,
    science_config_path: Path | None = None,
) -> PipelineContext:
    """
    Load configuration, environment variables, and construct the pipeline context.

    Parameters
    ----------
    config_path:
        Path to the pipeline YAML. Defaults to ``config/pipeline.yaml``.
    repo_root:
        Root of the repository. Defaults to ``Path.cwd()``.
    output_dir:
        Directory for generated artifacts. Defaults to ``repo_root / 'outputs'``.
    ablations:
        Comma-separated ablation flags (see `AblationSwitch`).
    env_keys:
        Environment variables to capture for provenance logging.
    constraints_path:
        Optional path to a course constraints YAML that overrides config.course.
    notebook_slug_override:
        Optional notebook slug override for Notebook exports.
    notebook_auto_create_override:
        Force-enable/disable automatic notebook creation before exports.
    science_config_path:
        Optional path to the scientific evaluation config (defaults to
        ``config/scientific_config.yaml`` when present).
    """

    repo_root = (repo_root or Path.cwd()).resolve()
    dotenv_path = repo_root / ".env"
    load_dotenv(dotenv_path)  # make repo-scoped .env values available even when running elsewhere
    # Always export the resolved repo root so downstream tools (CodeAct, wm-inspect,
    # portal hooks) stay aligned with the CLI argument even when the env var was
    # previously set for a different checkout.
    os.environ["COURSEGEN_REPO_ROOT"] = str(repo_root)
    config_path = (config_path or DEFAULT_CONFIG_PATH).resolve()
    env_science_override = os.getenv("COURSEGEN_SCIENCE_CONFIG")
    if env_science_override and not science_config_path:
        science_config_path = Path(env_science_override)
    default_science_path = repo_root / "config" / "scientific_config.yaml"
    if science_config_path is None:
        science_config_path = default_science_path if default_science_path.exists() else None
    output_dir = (output_dir or (repo_root / DEFAULT_OUTPUT_DIR)).resolve()

    config: PipelineConfig = load_pipeline_config(config_path, base_dir=repo_root)

    if constraints_path is not None:
        constraints = load_course_constraints(constraints_path.resolve())
        config = config.model_copy(update={"course": constraints})

    if dataset_dir_override or world_model_store_override:
        world_model_cfg = config.world_model
        update_payload = {}
        if dataset_dir_override:
            update_payload["dataset_dir"] = dataset_dir_override.resolve()
        if world_model_store_override:
            update_payload["sqlite_path"] = world_model_store_override.resolve()
        world_model_cfg = world_model_cfg.model_copy(update=update_payload)
        config = config.model_copy(update={"world_model": world_model_cfg})
    if notebook_slug_override or notebook_auto_create_override is not None:
        notebook_updates = {}
        if notebook_slug_override:
            notebook_updates["notebook_slug"] = notebook_slug_override
        if notebook_auto_create_override is not None:
            notebook_updates["auto_create"] = notebook_auto_create_override
        notebook_cfg = config.notebook.model_copy(update=notebook_updates)
        config = config.model_copy(update={"notebook": notebook_cfg})

    ablation_cfg: AblationConfig = parse_ablation_flag(ablations)

    paths = PipelinePaths(
        repo_root=repo_root,
        output_dir=output_dir,
        artifacts_dir=output_dir / "artifacts",
        evaluations_dir=output_dir / "evaluations",
        logs_dir=output_dir / "logs",
    )
    provenance = ProvenanceLogger(paths.logs_dir / "provenance.jsonl")
    env_snapshot = _capture_env(env_keys)
    science_config, science_config_resolved = _load_scientific_config(science_config_path)

    ctx = PipelineContext(
        config=config,
        ablations=ablation_cfg,
        paths=paths,
        env=env_snapshot,
        provenance=provenance,
        science_config=science_config,
        science_config_path=science_config_resolved,
    )

    if science_config is not None and science_config_resolved is not None:
        ctx.provenance.log(
            ProvenanceEvent(
                stage="science_config",
                message="Scientific evaluation config loaded",
                agent="ccopilot.pipeline",
                payload={
                    "path": str(science_config_resolved),
                    "enabled": _science_config_enabled(science_config),
                },
            )
        )

    try:
        ctx.dspy_handles = configure_dspy_models(config.models)
    except DSPyConfigurationError as exc:
        raise RuntimeError("Unable to configure DSPy/OpenAI models") from exc

    ctx.provenance.log(
        ProvenanceEvent(
            stage="bootstrap",
            message="DSPy OpenAI models configured",
            agent="ccopilot.pipeline",
            payload={
                "teacher_model": config.models.teacher_model,
                "ta_model": config.models.ta_model,
                "student_model": config.models.student_model,
            },
        )
    )

    _ensure_dataset_exists(config.world_model.dataset_dir)
    _ensure_notebook_export_dir(ctx.paths.output_dir)
    if ctx.ablations.use_world_model:
        _refresh_world_model_if_needed(ctx, ingest_before_run)
    else:
        LOGGER.info("World model ablated; skipping ingest and snapshot checks.")
    _apply_notebook_env(ctx)

    return ctx


def _load_scientific_config(path: Path | None) -> tuple[Dict[str, object] | None, Path | None]:
    if path is None:
        return None, None
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        LOGGER.debug("Scientific config not found at %s; skipping", resolved)
        return None, None
    try:
        with resolved.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Invalid scientific config at {resolved}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Scientific config at {resolved} must be a mapping")
    return payload, resolved


def _science_config_enabled(config: Dict[str, object] | None) -> bool:
    if not config:
        return True
    enabled = config.get("enabled")
    if isinstance(enabled, bool):
        return enabled
    eval_cfg = config.get("evaluation_metrics")
    if isinstance(eval_cfg, dict):
        eval_enabled = eval_cfg.get("enabled")
        if isinstance(eval_enabled, bool):
            return eval_enabled
    return True


def _ensure_dataset_exists(dataset_dir: Path) -> None:
    resolved = dataset_dir.expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(
            f"Handcrafted dataset not found at {resolved}. Run scripts/ingest_handcrafted.py or pass --dataset-dir with a valid path."
        )
    os.environ["COURSEGEN_DATASET_DIR"] = str(resolved)


def _ensure_notebook_export_dir(output_dir: Path) -> None:
    default_export_dir = (output_dir / "notebook_exports").expanduser().resolve()
    if "OPEN_NOTEBOOK_EXPORT_DIR" not in os.environ:
        os.environ["OPEN_NOTEBOOK_EXPORT_DIR"] = str(default_export_dir)
    default_export_dir.mkdir(parents=True, exist_ok=True)


def _refresh_world_model_if_needed(ctx: PipelineContext, ingest_requested: bool) -> None:
    sqlite_path = ctx.config.world_model.sqlite_path
    if ingest_requested or not sqlite_path.exists():
        if not sqlite_path.exists():
            LOGGER.info("World model store %s missing; ingesting fresh snapshot.", sqlite_path)
        _ingest_world_model(ctx)
    else:
        LOGGER.debug("World model store present at %s; skipping ingest.", sqlite_path)


def _ingest_world_model(ctx: PipelineContext) -> None:
    dataset_dir = ctx.config.world_model.dataset_dir
    sqlite_path = ctx.config.world_model.sqlite_path
    snapshot_path = ctx.paths.artifacts_dir / "world_model_snapshot.jsonl"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    ctx.provenance.log(
        ProvenanceEvent(
            stage="ingest",
            message=f"Refreshing world model from {dataset_dir}",
            agent="ingest_handcrafted",
            payload={
                "dataset_dir": str(dataset_dir),
                "sqlite_path": str(sqlite_path),
                "snapshot": str(snapshot_path),
            },
        )
    )
    summary = ingest_handcrafted.ingest(dataset_dir, sqlite_path, jsonl_path=snapshot_path)
    ctx.provenance.log(
        ProvenanceEvent(
            stage="ingest",
            message="World model refreshed",
            agent="ingest_handcrafted",
            payload={**summary, "snapshot": str(snapshot_path)},
        )
    )


def _apply_notebook_env(ctx: PipelineContext) -> None:
    """Export notebook configuration to environment variables for downstream tools."""

    notebook_cfg = ctx.config.notebook
    applied: dict[str, object] = {}

    if notebook_cfg.api_base:
        os.environ["OPEN_NOTEBOOK_API_BASE"] = notebook_cfg.api_base
        applied["api_base"] = notebook_cfg.api_base

    if notebook_cfg.auth_token:
        os.environ["OPEN_NOTEBOOK_API_KEY"] = notebook_cfg.auth_token
        applied["token_provided"] = True
    elif "OPEN_NOTEBOOK_API_KEY" in os.environ:
        applied.setdefault("token_provided", True)

    if notebook_cfg.notebook_slug:
        os.environ["OPEN_NOTEBOOK_SLUG"] = notebook_cfg.notebook_slug
        applied["notebook_slug"] = notebook_cfg.notebook_slug

    os.environ["OPEN_NOTEBOOK_AUTO_CREATE"] = "1" if notebook_cfg.auto_create else "0"
    applied["auto_create"] = notebook_cfg.auto_create

    if applied:
        ctx.provenance.log(
            ProvenanceEvent(
                stage="bootstrap",
                message="Notebook API configuration exported to environment",
                agent="ccopilot.pipeline",
                payload={
                    "api_base": applied.get("api_base"),
                    "token_provided": applied.get("token_provided", False),
                    "notebook_slug": applied.get("notebook_slug"),
                    "auto_create": applied.get("auto_create"),
                },
            )
        )
