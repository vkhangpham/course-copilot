"""Data-related helper tools surfaced to CodeAct."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("coursegen.codeact.data")
DATA_ROOT = Path("data/handcrafted/database_systems")


def load_dataset_asset(name: str, base_dir: Path | None = None) -> dict[str, Any]:
    """Return the contents of a JSON/YAML dataset asset."""

    base = (base_dir or DATA_ROOT).expanduser().resolve()
    asset_path = base / name
    if not asset_path.exists():
        logger.warning("Dataset asset %s not found, returning stub payload", asset_path)
        return {"asset": name, "entries": []}

    text = asset_path.read_text(encoding="utf-8")
    suffix = asset_path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        try:
            data = yaml.safe_load(text) or {}
            if isinstance(data, dict):
                return data
            return {"asset": name, "data": data}
        except yaml.YAMLError as exc:  # noqa: PERF203 - informative log
            logger.warning("Failed to parse YAML asset %s: %s", asset_path, exc)
            return {"asset": name, "content": text}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Asset %s is not JSON/YAML; returning raw text", asset_path)
        return {"asset": name, "content": text}


def run_sql_query(query: str) -> list[dict[str, Any]]:
    """Stub DuckDB query runner pending full dataset hydration."""
    logger.debug("run_sql_query(query=%s)", query)
    return [{"query": query, "rows": []}]
