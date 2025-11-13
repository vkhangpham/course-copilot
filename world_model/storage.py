"""Lightweight SQLite-backed store for the CourseGen world model."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable


class WorldModelStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        """Create a connection, ensuring the parent directory exists."""

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self) -> None:
        schema_sql = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        with self._connect() as con:
            con.executescript(schema_sql)
            self._ensure_claim_columns(con)

    def _ensure_claim_columns(self, con: sqlite3.Connection) -> None:
        columns = {row[1] for row in con.execute("PRAGMA table_info(claims)")}
        if "confidence" not in columns:
            con.execute("ALTER TABLE claims ADD COLUMN confidence REAL DEFAULT 0.5")
        if "asserted_at" not in columns:
            con.execute("ALTER TABLE claims ADD COLUMN asserted_at TIMESTAMP")

    def execute(self, sql: str, params: tuple | None = None) -> int:
        """Execute a single SQL statement and return the last row id (if any)."""

        with self._connect() as con:
            cur = con.execute(sql, params or tuple())
            con.commit()
            return int(cur.lastrowid)

    def execute_many(self, sql: str, rows: Iterable[tuple]) -> None:
        buffered_rows = list(rows)
        if not buffered_rows:
            return
        with self._connect() as con:
            con.executemany(sql, buffered_rows)
            con.commit()

    def query(self, sql: str, params: tuple | None = None) -> list[tuple]:
        with self._connect() as con:
            cur = con.execute(sql, params or tuple())
            return cur.fetchall()
