"""Bootstrap helpers for the CourseGen pipeline."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv

from ccopilot.core.ablation import AblationConfig, parse_ablation_flag
from ccopilot.core.config import PipelineConfig, load_pipeline_config
from ccopilot.core.provenance import ProvenanceEvent, ProvenanceLogger

from .context import PipelineContext, PipelinePaths
from scripts import ingest_handcrafted


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
    """

    load_dotenv()  # make .env values available

    repo_root = (repo_root or Path.cwd()).resolve()
    config_path = (config_path or DEFAULT_CONFIG_PATH).resolve()
    output_dir = (output_dir or (repo_root / DEFAULT_OUTPUT_DIR)).resolve()

    config: PipelineConfig = load_pipeline_config(config_path)

    if dataset_dir_override or world_model_store_override:
        world_model_cfg = config.world_model
        update_payload = {}
        if dataset_dir_override:
            update_payload["dataset_dir"] = dataset_dir_override.resolve()
        if world_model_store_override:
            update_payload["sqlite_path"] = world_model_store_override.resolve()
        world_model_cfg = world_model_cfg.model_copy(update=update_payload)
        config = config.model_copy(update={"world_model": world_model_cfg})
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

    ctx = PipelineContext(
        config=config,
        ablations=ablation_cfg,
        paths=paths,
        env=env_snapshot,
        provenance=provenance,
    )

    _ensure_dataset_exists(config.world_model.dataset_dir)
    _refresh_world_model_if_needed(ctx, ingest_before_run)
    _apply_notebook_env(ctx)

    return ctx


def _ensure_dataset_exists(dataset_dir: Path) -> None:
    if not dataset_dir.exists():
        raise FileNotFoundError(
            f"Handcrafted dataset not found at {dataset_dir}. "
            "Run scripts/ingest_handcrafted.py or pass --dataset-dir with a valid path."
        )


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
                },
            )
        )
