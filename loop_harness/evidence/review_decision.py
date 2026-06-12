"""Human decisions for evidence review packages."""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ReviewDecisionStatus(str, Enum):
    """Review package decision status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewPackageDecision(BaseModel):
    """One human decision record linked to an evidence review package."""

    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    package_id: str
    scenario_id: str
    workflow_id: str
    baseline_run_id: str
    candidate_run_ids: list[str]
    recommended_action: str
    status: ReviewDecisionStatus = ReviewDecisionStatus.PENDING
    reason: str
    approval_required: bool = True
    comment: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    decided_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReviewPackageDecisionStore:
    """Persist review package decisions in SQLite."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def create(self, decision: ReviewPackageDecision) -> ReviewPackageDecision:
        """Create or replace one review package decision."""

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO evidence_review_decisions (
                    decision_id, package_id, scenario_id, workflow_id, baseline_run_id,
                    candidate_run_ids_json, recommended_action, status, reason,
                    approval_required, comment, created_at, decided_at, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(decision_id) DO UPDATE SET
                    package_id=excluded.package_id,
                    scenario_id=excluded.scenario_id,
                    workflow_id=excluded.workflow_id,
                    baseline_run_id=excluded.baseline_run_id,
                    candidate_run_ids_json=excluded.candidate_run_ids_json,
                    recommended_action=excluded.recommended_action,
                    status=excluded.status,
                    reason=excluded.reason,
                    approval_required=excluded.approval_required,
                    comment=excluded.comment,
                    created_at=excluded.created_at,
                    decided_at=excluded.decided_at,
                    metadata_json=excluded.metadata_json
                """,
                self._to_row(decision),
            )
        return decision

    def get(self, decision_id: str) -> ReviewPackageDecision | None:
        """Return one review decision by id."""

        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM evidence_review_decisions WHERE decision_id = ?",
                (decision_id,),
            ).fetchone()
        return None if row is None else self._from_row(row)

    def get_by_package(self, package_id: str) -> ReviewPackageDecision | None:
        """Return the latest review decision for one package id."""

        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT * FROM evidence_review_decisions
                WHERE package_id = ?
                ORDER BY created_at DESC, rowid DESC
                LIMIT 1
                """,
                (package_id,),
            ).fetchone()
        return None if row is None else self._from_row(row)

    def list(
        self,
        scenario_id: str | None = None,
        status: ReviewDecisionStatus | None = None,
    ) -> list[ReviewPackageDecision]:
        """List review decisions, optionally filtered by scenario and status."""

        clauses: list[str] = []
        params: list[str] = []
        if scenario_id is not None:
            clauses.append("scenario_id = ?")
            params.append(scenario_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM evidence_review_decisions {where} ORDER BY created_at, rowid",
                tuple(params),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def update_status(
        self,
        decision_id: str,
        status: ReviewDecisionStatus,
        comment: str,
    ) -> ReviewPackageDecision:
        """Update one pending decision status."""

        existing = self.get(decision_id)
        if existing is None:
            raise ValueError(f"Unknown review decision: {decision_id}")
        if existing.status != ReviewDecisionStatus.PENDING:
            raise ValueError(f"Review decision is already {existing.status.value}.")
        existing.status = status
        existing.comment = comment
        existing.decided_at = datetime.now(UTC)
        self.create(existing)
        return existing

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
                CREATE TABLE IF NOT EXISTS evidence_review_decisions (
                    decision_id TEXT PRIMARY KEY,
                    package_id TEXT NOT NULL,
                    scenario_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    baseline_run_id TEXT NOT NULL,
                    candidate_run_ids_json TEXT NOT NULL,
                    recommended_action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    approval_required INTEGER NOT NULL,
                    comment TEXT,
                    created_at TEXT NOT NULL,
                    decided_at TEXT,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_review_decisions_package "
                "ON evidence_review_decisions (package_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_review_decisions_scenario "
                "ON evidence_review_decisions (scenario_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_review_decisions_status "
                "ON evidence_review_decisions (status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_review_decisions_created "
                "ON evidence_review_decisions (created_at)"
            )

    @staticmethod
    def _to_row(decision: ReviewPackageDecision) -> tuple[Any, ...]:
        return (
            decision.decision_id,
            decision.package_id,
            decision.scenario_id,
            decision.workflow_id,
            decision.baseline_run_id,
            json.dumps(decision.candidate_run_ids, ensure_ascii=False),
            decision.recommended_action,
            decision.status.value,
            decision.reason,
            int(decision.approval_required),
            decision.comment,
            decision.created_at.isoformat(),
            decision.decided_at.isoformat() if decision.decided_at else None,
            json.dumps(decision.metadata, ensure_ascii=False, default=str),
        )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> ReviewPackageDecision:
        decided_at = row["decided_at"]
        return ReviewPackageDecision(
            decision_id=row["decision_id"],
            package_id=row["package_id"],
            scenario_id=row["scenario_id"],
            workflow_id=row["workflow_id"],
            baseline_run_id=row["baseline_run_id"],
            candidate_run_ids=[str(item) for item in json.loads(row["candidate_run_ids_json"])],
            recommended_action=row["recommended_action"],
            status=ReviewDecisionStatus(row["status"]),
            reason=row["reason"],
            approval_required=bool(row["approval_required"]),
            comment=row["comment"],
            created_at=datetime.fromisoformat(row["created_at"]).astimezone(UTC),
            decided_at=datetime.fromisoformat(decided_at).astimezone(UTC) if decided_at else None,
            metadata=json.loads(row["metadata_json"]),
        )
