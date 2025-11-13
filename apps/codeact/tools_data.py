"""Data/analytics helpers surfaced to CodeAct via a small wrapper class."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .tools.data import get_dataset_root, run_sql_query


class DataTools:
    """Expose dataset-backed SQL helpers to CodeAct in a stateful way.

    The class mirrors the interface sketched in PLAN.md: CodeAct receives a
    `run_sql` tool that executes read-only DuckDB queries over the handcrafted
    dataset. Under the hood we re-use the well-tested `run_sql_query`
    implementation so the behavior stays consistent across the function and
    object-based surfaces.
    """

    def __init__(self, scratch_dir: Path, dataset_dir: Path | None = None) -> None:
        self.scratch_dir = scratch_dir.expanduser().resolve()
        self.dataset_dir = (
            Path(dataset_dir).expanduser().resolve()
            if dataset_dir is not None
            else get_dataset_root()
        )
        self.scratch_dir.mkdir(parents=True, exist_ok=True)

    def run_sql(self, sql: str) -> List[Dict[str, Any]]:
        """Execute a read-only SQL query over the handcrafted dataset."""

        return run_sql_query(sql, dataset_dir=self.dataset_dir)
