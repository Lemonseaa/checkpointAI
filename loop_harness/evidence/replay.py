"""Replay validation for portable evidence review packages."""

from __future__ import annotations

from pydantic import BaseModel, Field

from loop_harness.evidence.models import StoredEvidenceRun
from loop_harness.evidence.review_package import EvidenceReviewPackage


class ReplayValidationResult(BaseModel):
    """Result of validating a review package against current stored evidence."""

    package_id: str
    valid: bool
    missing_run_ids: list[str] = Field(default_factory=list)
    drifted_run_ids: list[str] = Field(default_factory=list)
    summary: str


class PackageReplayValidator:
    """Validate that a package can still be reproduced from stored evidence."""

    def validate(
        self,
        package: EvidenceReviewPackage,
        stored_runs: list[StoredEvidenceRun],
    ) -> ReplayValidationResult:
        """Validate run presence and metric-key drift."""

        stored_by_id = {stored.run.run_id: stored for stored in stored_runs}
        expected_ids = [package.baseline_run_id, *package.candidate_run_ids]
        missing = [run_id for run_id in expected_ids if run_id not in stored_by_id]
        drifted: list[str] = []
        for point in package.chart.candidate_points:
            stored = stored_by_id.get(point.run_id)
            if stored is None:
                continue
            expected_metrics = [
                metric
                for metric in ["total_return", "sharpe", "max_drawdown", "win_rate", "turnover"]
                if getattr(point, metric) is not None
            ]
            if any(metric not in stored.run.metrics for metric in expected_metrics):
                drifted.append(point.run_id)
        valid = not missing and not drifted
        summary = "Review package is replay-valid." if valid else (
            f"Review package is not replay-valid; missing={missing}, drifted={drifted}."
        )
        return ReplayValidationResult(
            package_id=package.package_id,
            valid=valid,
            missing_run_ids=missing,
            drifted_run_ids=drifted,
            summary=summary,
        )
