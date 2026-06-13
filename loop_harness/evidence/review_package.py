"""Portable evidence review packages for human and Hermes handoff."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from loop_harness.evidence.charts import OptimizationChartPayload
from loop_harness.evidence.gap import EvidenceGapReport
from loop_harness.evidence.graph import WorkflowGraphPayload
from loop_harness.evidence.models import EvidenceReport, StoredEvidenceRun


class EvidenceReviewPackage(BaseModel):
    """Portable evidence bundle for one baseline/candidate review."""

    package_id: str
    workflow_id: str
    scenario_id: str
    baseline_run_id: str
    candidate_run_ids: list[str]
    graph: WorkflowGraphPayload
    chart: OptimizationChartPayload
    comparison_reports: list[EvidenceReport]
    gap_summary: str
    recommended_action: str
    markdown: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceReviewPackageBuilder:
    """Build review packages from already-derived evidence objects."""

    def build(
        self,
        *,
        baseline: StoredEvidenceRun,
        candidates: list[StoredEvidenceRun],
        graph: WorkflowGraphPayload,
        chart: OptimizationChartPayload,
        comparison_reports: list[EvidenceReport],
        gap_reports: list[EvidenceGapReport],
    ) -> EvidenceReviewPackage:
        """Build one portable review package."""

        recommended_action = self._recommended_action(chart)
        package = EvidenceReviewPackage(
            package_id=self._package_id(baseline.run.workflow_id, baseline.run.run_id, len(candidates)),
            workflow_id=baseline.run.workflow_id,
            scenario_id=baseline.run.scenario_id,
            baseline_run_id=baseline.run.run_id,
            candidate_run_ids=[candidate.run.run_id for candidate in candidates],
            graph=graph,
            chart=chart,
            comparison_reports=comparison_reports,
            gap_summary=self._gap_summary(gap_reports),
            recommended_action=recommended_action,
            markdown="",
            metadata={
                "best_candidate_run_id": chart.best_candidate_run_id,
                "candidate_count": len(candidates),
                "comparison_count": len(comparison_reports),
            },
        )
        package.markdown = self._markdown(package)
        return package

    @staticmethod
    def _package_id(workflow_id: str, baseline_run_id: str, candidate_count: int) -> str:
        raw = f"review_{workflow_id}_{baseline_run_id}_{candidate_count}"
        return re.sub(r"[^A-Za-z0-9_]+", "_", raw)

    @staticmethod
    def _recommended_action(chart: OptimizationChartPayload) -> str:
        if not chart.candidate_points:
            return "collect_more_evidence"
        if all(point.candidate_quality == "weak" or point.guardrail_status == "violated" for point in chart.candidate_points):
            return "reject_or_refine"
        best = next((point for point in chart.candidate_points if point.best_candidate), None)
        if best is None:
            return "collect_more_evidence"
        if best.run_kind in {"fixture", "synthetic"}:
            return "collect_more_evidence"
        if best.guardrail_status == "violated":
            return "reject_or_refine"
        return "review_for_paper"

    @staticmethod
    def _gap_summary(gap_reports: list[EvidenceGapReport]) -> str:
        total = sum(len(report.gaps) for report in gap_reports)
        rejected = [report.run_id for report in gap_reports if report.status == "rejected"]
        if rejected:
            return f"{total} evidence gaps across candidates; rejected runs: {', '.join(rejected)}."
        return f"{total} evidence gaps across candidates."

    @staticmethod
    def _markdown(package: EvidenceReviewPackage) -> str:
        lines = [
            "# Evidence Review Package",
            "",
            f"Package: {package.package_id}",
            f"Workflow: {package.workflow_id}",
            f"Scenario: {package.scenario_id}",
            f"Baseline: {package.baseline_run_id}",
            f"Candidates: {', '.join(package.candidate_run_ids)}",
            "",
            "## Best Candidate",
            str(package.chart.best_candidate_run_id or "none"),
            "",
            "## Guardrail Summary",
            package.chart.guardrail_summary,
            "",
            "## Evidence Gaps",
            package.gap_summary,
            "",
            "## Comparison Summaries",
        ]
        for report in package.comparison_reports:
            lines.append(f"- {report.candidate_run_id}: {report.summary}")
        lines.extend(["", "## Quant Paper Trading Decision"])
        lines.extend(EvidenceReviewPackageBuilder._quant_decision_lines(package))
        lines.extend(
            [
                "",
                "## Next Action",
                package.recommended_action,
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _quant_decision_lines(package: EvidenceReviewPackage) -> list[str]:
        best = next((point for point in package.chart.candidate_points if point.best_candidate), None)
        candidate_ids = ", ".join(package.candidate_run_ids) or "none"
        paper_ready = package.recommended_action == "review_for_paper"
        changed = "unknown"
        if best is not None:
            config = best.metadata.get("config", {})
            if isinstance(config, dict):
                changed = ", ".join(f"{key}={value}" for key, value in config.items()) or "config captured"
        improved = []
        worsened = []
        for report in package.comparison_reports:
            comparison = report.comparison
            if comparison is None:
                continue
            for name, evaluation in comparison.metric_evaluations.items():
                if evaluation.improved:
                    improved.append(name)
                elif name in comparison.business_metric_diffs:
                    worsened.append(name)
        return [
            f"- 这次测试了什么策略：{candidate_ids}",
            f"- baseline 是什么：{package.baseline_run_id}",
            f"- candidate 改了什么：{changed}",
            f"- 哪些指标变好：{', '.join(sorted(set(improved))) or 'none'}",
            f"- 哪些风险变坏：{', '.join(sorted(set(worsened))) or 'none'}",
            f"- 是否建议进入 paper trading：{'是' if paper_ready else '否'}",
            "- 人需要审批什么：是否接受该候选进入下一阶段人工复核或模拟盘观察",
        ]
