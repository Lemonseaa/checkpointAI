"""Human decision memory summaries for evidence review."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, Field

from loop_harness.decision import DecisionKind, DecisionLogStore, DecisionRecord


class DecisionMemorySummary(BaseModel):
    """Aggregated human approval/rejection tendencies."""

    scenario_id: str
    approved_count: int
    rejected_count: int
    approved_patterns: list[str] = Field(default_factory=list)
    rejected_patterns: list[str] = Field(default_factory=list)
    summary: str


class HumanDecisionMemory:
    """Summarize operator decisions without taking over decision rights."""

    def __init__(self, db_path: str | Path) -> None:
        self.store = DecisionLogStore(db_path)

    def summarize(self, scenario_id: str) -> DecisionMemorySummary:
        """Summarize approval/rejection history for one scenario."""

        records = self.store.list(scenario_id=scenario_id)
        approved = [record for record in records if record.kind == DecisionKind.APPROVE]
        rejected = [record for record in records if record.kind == DecisionKind.REJECT]
        approved_patterns = self._patterns(approved)
        rejected_patterns = self._patterns(rejected)
        return DecisionMemorySummary(
            scenario_id=scenario_id,
            approved_count=len(approved),
            rejected_count=len(rejected),
            approved_patterns=approved_patterns,
            rejected_patterns=rejected_patterns,
            summary=(
                f"Scenario {scenario_id}: {len(approved)} approvals, {len(rejected)} rejections. "
                "Use this as decision context, not automatic authority."
            ),
        )

    @staticmethod
    def _patterns(records: Sequence[DecisionRecord]) -> list[str]:
        counter: Counter[str] = Counter()
        for record in records:
            details = getattr(record, "details", {})
            if isinstance(details, dict):
                proposal_kind = details.get("proposal_kind")
                expected_metric = details.get("expected_metric")
                if isinstance(proposal_kind, str):
                    counter[proposal_kind] += 1
                if isinstance(expected_metric, str):
                    counter[expected_metric] += 1
        return [item for item, _count in counter.most_common(5)]
