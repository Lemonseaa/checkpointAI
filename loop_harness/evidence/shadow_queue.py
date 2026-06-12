"""Shadow replay queue for evidence proposals."""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ShadowReplayItem(BaseModel):
    """One queued shadow replay request."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scenario_id: str
    proposal_id: str
    baseline_run_id: str
    candidate_run_id: str
    status: str = "pending"
    result: dict[str, Any] = Field(default_factory=dict)


class ShadowReplayQueueStore:
    """SQLite-backed shadow replay queue."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def enqueue(self, item: ShadowReplayItem) -> str:
        """Insert or update one queue item."""

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO evidence_shadow_queue (id, scenario_id, proposal_id, status, item_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET status=excluded.status, item_json=excluded.item_json
                """,
                (item.id, item.scenario_id, item.proposal_id, item.status, item.model_dump_json()),
            )
        return item.id

    def list(self, scenario_id: str | None = None, status: str | None = None) -> list[ShadowReplayItem]:
        """List queued items."""

        clauses: list[str] = []
        params: list[str] = []
        if scenario_id is not None:
            clauses.append("scenario_id = ?")
            params.append(scenario_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT item_json FROM evidence_shadow_queue {where} ORDER BY rowid",
                tuple(params),
            ).fetchall()
        return [ShadowReplayItem.model_validate(json.loads(row["item_json"])) for row in rows]

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence_shadow_queue (
                    id TEXT PRIMARY KEY,
                    scenario_id TEXT NOT NULL,
                    proposal_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    item_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_shadow_queue_scenario "
                "ON evidence_shadow_queue (scenario_id)"
            )
