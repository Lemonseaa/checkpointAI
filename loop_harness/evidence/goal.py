"""Human-owned optimization goal profiles."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class OptimizationGoalProfile(BaseModel):
    """User-defined optimization goals for one scenario."""

    scenario_id: str
    primary_metrics: list[str]
    guardrail_metrics: list[str] = Field(default_factory=list)
    max_cost_increase: float = 0.0
    max_risk_level: str = "approval"
    preferences: dict[str, Any] = Field(default_factory=dict)


class OptimizationGoalStore:
    """SQLite storage for human-owned optimization goal profiles."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def save(self, profile: OptimizationGoalProfile) -> OptimizationGoalProfile:
        """Insert or update one profile."""

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO optimization_goal_profiles (scenario_id, profile_json)
                VALUES (?, ?)
                ON CONFLICT(scenario_id) DO UPDATE SET profile_json=excluded.profile_json
                """,
                (profile.scenario_id, profile.model_dump_json()),
            )
        return profile

    def get(self, scenario_id: str) -> OptimizationGoalProfile | None:
        """Return one profile."""

        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT profile_json FROM optimization_goal_profiles WHERE scenario_id = ?",
                (scenario_id,),
            ).fetchone()
        if row is None:
            return None
        return OptimizationGoalProfile.model_validate(json.loads(row["profile_json"]))

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
                CREATE TABLE IF NOT EXISTS optimization_goal_profiles (
                    scenario_id TEXT PRIMARY KEY,
                    profile_json TEXT NOT NULL
                )
                """
            )
