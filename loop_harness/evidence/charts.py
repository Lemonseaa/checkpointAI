"""UI-ready optimization chart payloads for evidence runs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from loop_harness.evidence.models import EvidenceReport, StoredEvidenceRun


class CandidateChartPoint(BaseModel):
    """One candidate point in an optimization chart."""

    run_id: str
    scenario_id: str
    run_kind: str
    total_return: float | None = None
    sharpe: float | None = None
    max_drawdown: float | None = None
    win_rate: float | None = None
    turnover: float | None = None
    objective_score: float | None = None
    guardrail_status: str
    candidate_quality: str
    best_candidate: bool = False
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MetricTrendPoint(BaseModel):
    """One metric value for a run-level trend chart."""

    run_id: str
    metric: str
    value: float
    role: str


class OptimizationChartPayload(BaseModel):
    """Complete UI-ready chart payload for baseline/candidate impact."""

    workflow_id: str
    scenario_id: str
    baseline_run_id: str
    baseline_metrics: dict[str, float]
    candidate_points: list[CandidateChartPoint]
    metric_trends: list[MetricTrendPoint]
    chart_fields: list[str]
    guardrail_summary: str
    best_candidate_run_id: str | None = None
    summary: str


class OptimizationChartBuilder:
    """Build chart payloads from stored evidence runs and comparison reports."""

    CHART_FIELDS = ["total_return", "sharpe", "max_drawdown", "objective_score"]

    def build(
        self,
        *,
        baseline: StoredEvidenceRun,
        candidates: list[StoredEvidenceRun],
        comparisons: list[EvidenceReport] | None = None,
    ) -> OptimizationChartPayload:
        """Build an optimization chart payload."""

        comparison_by_candidate = {
            report.candidate_run_id: report
            for report in comparisons or []
            if report.candidate_run_id is not None
        }
        candidate_points = [
            self._candidate_point(candidate, comparison_by_candidate.get(candidate.run.run_id))
            for candidate in candidates
        ]
        best_candidate = self._best_candidate(candidate_points)
        if best_candidate is not None:
            for point in candidate_points:
                point.best_candidate = point.run_id == best_candidate.run_id
        metric_trends = self._metric_trends(baseline, candidates)
        return OptimizationChartPayload(
            workflow_id=baseline.run.workflow_id,
            scenario_id=baseline.run.scenario_id,
            baseline_run_id=baseline.run.run_id,
            baseline_metrics=baseline.run.metrics,
            candidate_points=candidate_points,
            metric_trends=metric_trends,
            chart_fields=self.CHART_FIELDS,
            guardrail_summary=self._guardrail_summary(candidate_points),
            best_candidate_run_id=best_candidate.run_id if best_candidate else None,
            summary=self._summary(baseline.run.run_id, candidate_points, best_candidate),
        )

    def _candidate_point(self, candidate: StoredEvidenceRun, report: EvidenceReport | None) -> CandidateChartPoint:
        metrics = candidate.run.metrics
        max_drawdown = metrics.get("max_drawdown")
        sharpe = metrics.get("sharpe")
        guardrail_status = self._guardrail_status(candidate)
        candidate_quality = self._candidate_quality(sharpe, guardrail_status)
        objective_score = report.comparison.objective_score if report and report.comparison else None
        return CandidateChartPoint(
            run_id=candidate.run.run_id,
            scenario_id=candidate.run.scenario_id,
            run_kind=candidate.run.run_kind.value,
            total_return=metrics.get("total_return"),
            sharpe=sharpe,
            max_drawdown=max_drawdown,
            win_rate=metrics.get("win_rate"),
            turnover=metrics.get("turnover"),
            objective_score=objective_score,
            guardrail_status=guardrail_status,
            candidate_quality=candidate_quality,
            summary=(
                f"{candidate.run.run_id}: sharpe={sharpe}, "
                f"max_drawdown={max_drawdown}, guardrail={guardrail_status}."
            ),
            metadata={
                "config": candidate.run.config,
                "quality": candidate.report.evidence.get("quality", {}),
            },
        )

    @staticmethod
    def _metric_trends(baseline: StoredEvidenceRun, candidates: list[StoredEvidenceRun]) -> list[MetricTrendPoint]:
        points: list[MetricTrendPoint] = []
        for metric, value in baseline.run.metrics.items():
            points.append(MetricTrendPoint(run_id=baseline.run.run_id, metric=metric, value=value, role="baseline"))
        for candidate in candidates:
            for metric, value in candidate.run.metrics.items():
                points.append(MetricTrendPoint(run_id=candidate.run.run_id, metric=metric, value=value, role="candidate"))
        return points

    @staticmethod
    def _best_candidate(points: list[CandidateChartPoint]) -> CandidateChartPoint | None:
        eligible = [point for point in points if point.guardrail_status != "violated"]
        if not eligible:
            return None
        if any(point.objective_score is not None for point in eligible):
            return max(eligible, key=lambda point: point.objective_score if point.objective_score is not None else -999.0)
        return max(eligible, key=lambda point: point.sharpe if point.sharpe is not None else -999.0)

    @staticmethod
    def _guardrail_status(candidate: StoredEvidenceRun) -> str:
        drawdown = candidate.run.metrics.get("max_drawdown")
        if drawdown is None:
            return "unknown"
        threshold = 0.2
        raw_schema = candidate.run.metric_schema.get("max_drawdown", {})
        if isinstance(raw_schema, dict) and isinstance(raw_schema.get("threshold"), int | float):
            threshold = float(raw_schema["threshold"])
        return "violated" if drawdown > threshold else "ok"

    @staticmethod
    def _candidate_quality(sharpe: float | None, guardrail_status: str) -> str:
        if guardrail_status == "violated" or sharpe is None or sharpe < 0.7:
            return "weak"
        return "candidate"

    @staticmethod
    def _guardrail_summary(points: list[CandidateChartPoint]) -> str:
        violations = [point.run_id for point in points if point.guardrail_status == "violated"]
        if not violations:
            return "No candidates violated configured guardrails."
        return f"{len(violations)} candidates violated guardrails: {', '.join(violations[:5])}."

    @staticmethod
    def _summary(
        baseline_run_id: str,
        points: list[CandidateChartPoint],
        best_candidate: CandidateChartPoint | None,
    ) -> str:
        if not points:
            return f"Baseline {baseline_run_id} has no candidate runs to chart."
        best = best_candidate.run_id if best_candidate else "none"
        violations = len([point for point in points if point.guardrail_status == "violated"])
        return f"Baseline {baseline_run_id} compared with {len(points)} candidates; best={best}; guardrail_violations={violations}."
