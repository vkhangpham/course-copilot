"""Data/analytics tools exposed to TAs via CodeAct."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import duckdb


class DataTools:
    def __init__(self, scratch_dir: Path):
        self.scratch_dir = scratch_dir
        self.connection = duckdb.connect(str(scratch_dir / "codeact.duckdb"))

    def run_sql(self, sql: str) -> Dict[str, Any]:  # pragma: no cover - placeholder
        raise NotImplementedError("SQL execution wiring will happen alongside CodeAct setup.")
