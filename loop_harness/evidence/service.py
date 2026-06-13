"""Service layer for external workflow evidence ingestion and reporting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loop_harness.evaluation import EvidenceDecision, EvidenceEvaluationEngine
from loop_harness.evidence.baseline_store import EvidenceBaselineStore
from loop_harness.evidence.charts import OptimizationChartBuilder, OptimizationChartPayload
from loop_harness.evidence.contract import WorkflowContractValidator
from loop_harness.evidence.csv_import import QuantBacktestCSVImporter, QuantCSVImportResult
from loop_harness.evidence.gap import EvidenceGapReport, build_gap_report
from loop_harness.evidence.graph import WorkflowGraphBuilder, WorkflowGraphPayload
from loop_harness.evidence.models import (
    DecisionRecommendation,
    EvidenceReport,
    ExternalWorkflowRun,
    IngestResult,
    StoredEvidenceRun,
    WorkflowVisualization,
)
from loop_harness.evidence.quality import EvidenceQualityGate
from loop_harness.evidence.quant_contracts import QuantEvidenceContractValidator
from loop_harness.evidence.replay import PackageReplayValidator, ReplayValidationResult
from loop_harness.evidence.review_decision import (
    ReviewDecisionStatus,
    ReviewPackageDecision,
    ReviewPackageDecisionStore,
)
from loop_harness.evidence.review_package import EvidenceReviewPackage, EvidenceReviewPackageBuilder
from loop_harness.evidence.storage import EvidenceStore
from loop_harness.evidence.workflow_map import (
    NodeEvidenceDetail,
    WorkflowMapSummary,
    build_node_detail,
    build_workflow_map,
)
from loop_harness.metrics import (
    MetricCategory,
    MetricDirection,
    MetricSchema,
    MetricSchemaRegistry,
)
from loop_harness.shadow import MetricComparator, RunKind


class EvidenceService:
    """Coordinate ingest, visualization, comparison, and reports."""

    def __init__(self, store: EvidenceStore) -> None:
        self.store = store

    def ingest_file(self, path: str | Path) -> IngestResult:
        """Load and ingest one external workflow run JSON file."""

        payload = self._load_payload(path)
        return self.ingest_payload(payload)

    def ingest_payload(self, payload: dict[str, Any]) -> IngestResult:
        """Normalize one external workflow run payload and persist derived evidence."""

        validation = WorkflowContractValidator().validate(payload)
        if not validation.accepted:
            details = "; ".join(issue.message for issue in validation.issues)
            raise ValueError(f"Workflow contract rejected: {details}")
        if self._is_quant_payload(payload):
            quant_validation = QuantEvidenceContractValidator().validate(payload)
            if not quant_validation.accepted:
                details = "; ".join(issue.message for issue in quant_validation.issues)
                raise ValueError(f"Quant evidence contract rejected: {details}")
        run = ExternalWorkflowRun.model_validate(payload)
        visualization = self.build_visualization(run)
        report = self.build_report(run, visualization)
        self.store.save(run, visualization, report)
        return IngestResult(run=run, visualization=visualization, report=report)

    def ingest_quant_csv(
        self,
        path: str | Path,
        *,
        workflow_id: str,
        scenario_id: str,
        run_kind: str,
    ) -> QuantCSVImportResult:
        """Import quant backtest CSV rows as evidence runs."""

        payloads = QuantBacktestCSVImporter().load(
            path,
            workflow_id=workflow_id,
            scenario_id=scenario_id,
            run_kind=run_kind,
        )
        run_ids: list[str] = []
        for payload in payloads:
            result = self.ingest_payload(payload)
            run_ids.append(result.run.run_id)
        return QuantCSVImportResult(
            workflow_id=workflow_id,
            scenario_id=scenario_id,
            run_kind=run_kind,
            imported_count=len(run_ids),
            run_ids=run_ids,
        )

    def workflow_map(self, workflow_id: str) -> WorkflowMapSummary:
        """Return an aggregated workflow map for one workflow."""

        return build_workflow_map(self.store.list_runs(workflow_id=workflow_id), workflow_id)

    def gap_report(self, run_id: str) -> EvidenceGapReport:
        """Return evidence gaps for one run."""

        stored = self.store.get_run(run_id)
        if stored is None:
            raise ValueError(f"Unknown evidence run: {run_id}")
        return build_gap_report(stored)

    def node_detail(self, run_id: str, node_id: str) -> NodeEvidenceDetail:
        """Return node-level evidence detail."""

        stored = self.store.get_run(run_id)
        if stored is None:
            raise ValueError(f"Unknown evidence run: {run_id}")
        return build_node_detail(stored, node_id)

    def graph_for_run(self, run_id: str) -> WorkflowGraphPayload:
        """Return graph payload for one run."""

        stored = self.store.get_run(run_id)
        if stored is None:
            raise ValueError(f"Unknown evidence run: {run_id}")
        return WorkflowGraphBuilder().build(stored)

    def graph_for_workflow(self, workflow_id: str) -> WorkflowGraphPayload:
        """Return graph payload for the latest run in one workflow."""

        runs = self.store.list_runs(workflow_id=workflow_id)
        if not runs:
            raise ValueError(f"Unknown workflow: {workflow_id}")
        return WorkflowGraphBuilder().build(runs[-1])

    def optimization_chart(self, workflow_id: str) -> OptimizationChartPayload:
        """Return an optimization chart for one workflow using its pinned or first baseline."""

        runs = self.store.list_runs(workflow_id=workflow_id)
        if not runs:
            raise ValueError(f"Unknown workflow: {workflow_id}")
        baseline_id = EvidenceBaselineStore(self.store.path).get_baseline(workflow_id)
        baseline_run_id = baseline_id.baseline_run_id if baseline_id is not None else runs[0].run.run_id
        candidates = [run.run.run_id for run in runs if run.run.run_id != baseline_run_id]
        return self.optimization_chart_for_runs(baseline_run_id, candidates)

    def optimization_chart_for_runs(
        self,
        baseline_run_id: str,
        candidate_run_ids: list[str],
    ) -> OptimizationChartPayload:
        """Return an optimization chart for explicit baseline/candidate runs."""

        baseline = self.store.get_run(baseline_run_id)
        if baseline is None:
            raise ValueError(f"Unknown baseline run: {baseline_run_id}")
        candidates = []
        comparisons = []
        for candidate_run_id in candidate_run_ids:
            candidate = self.store.get_run(candidate_run_id)
            if candidate is None:
                raise ValueError(f"Unknown candidate run: {candidate_run_id}")
            candidates.append(candidate)
            comparisons.append(self.compare(baseline_run_id, candidate_run_id))
        return OptimizationChartBuilder().build(
            baseline=baseline,
            candidates=candidates,
            comparisons=comparisons,
        )

    def review_package_for_runs(
        self,
        baseline_run_id: str,
        candidate_run_ids: list[str],
    ) -> EvidenceReviewPackage:
        """Build a portable evidence review package."""

        if not candidate_run_ids:
            raise ValueError("Review package requires at least one candidate run.")
        baseline = self.store.get_run(baseline_run_id)
        if baseline is None:
            raise ValueError(f"Unknown baseline run: {baseline_run_id}")
        candidates = self._stored_candidates(candidate_run_ids)
        comparisons = [self.compare(baseline_run_id, candidate.run.run_id) for candidate in candidates]
        chart = self.optimization_chart_for_runs(baseline_run_id, candidate_run_ids)
        graph_run_id = chart.best_candidate_run_id or candidate_run_ids[0]
        graph = self.graph_for_run(graph_run_id)
        gaps = [self.gap_report(candidate.run.run_id) for candidate in candidates]
        return EvidenceReviewPackageBuilder().build(
            baseline=baseline,
            candidates=candidates,
            graph=graph,
            chart=chart,
            comparison_reports=comparisons,
            gap_reports=gaps,
        )

    def validate_review_package(self, package: EvidenceReviewPackage) -> ReplayValidationResult:
        """Validate a review package against current stored evidence."""

        stored_runs = [
            stored
            for run_id in [package.baseline_run_id, *package.candidate_run_ids]
            if (stored := self.store.get_run(run_id)) is not None
        ]
        return self.validate_review_package_with_runs(package, stored_runs)

    @staticmethod
    def validate_review_package_with_runs(
        package: EvidenceReviewPackage,
        stored_runs: list[StoredEvidenceRun],
    ) -> ReplayValidationResult:
        """Validate a review package against provided stored runs."""

        return PackageReplayValidator().validate(package, stored_runs)

    def submit_review_package(self, package: EvidenceReviewPackage, reason: str) -> ReviewPackageDecision:
        """Submit a replay-valid package for human review."""

        cleaned_reason = reason.strip()
        if not cleaned_reason:
            raise ValueError("Review package submission requires a reason.")
        validation = self.validate_review_package(package)
        if not validation.valid:
            raise ValueError(f"Review package is not replay-valid: {validation.summary}")
        decision = ReviewPackageDecision(
            package_id=package.package_id,
            scenario_id=package.scenario_id,
            workflow_id=package.workflow_id,
            baseline_run_id=package.baseline_run_id,
            candidate_run_ids=package.candidate_run_ids,
            recommended_action=package.recommended_action,
            reason=cleaned_reason,
            metadata={
                "package_markdown": package.markdown,
                "best_candidate_run_id": package.metadata.get("best_candidate_run_id"),
                "guardrail_summary": package.chart.guardrail_summary,
                "gap_summary": package.gap_summary,
            },
        )
        return ReviewPackageDecisionStore(self.store.path).create(decision)

    def approve_review_package(self, decision_id: str, comment: str) -> ReviewPackageDecision:
        """Approve one pending review package decision."""

        return self._decide_review_package(decision_id, ReviewDecisionStatus.APPROVED, comment)

    def reject_review_package(self, decision_id: str, comment: str) -> ReviewPackageDecision:
        """Reject one pending review package decision."""

        return self._decide_review_package(decision_id, ReviewDecisionStatus.REJECTED, comment)

    def list_review_package_decisions(
        self,
        scenario_id: str | None = None,
        status: str | None = None,
    ) -> list[ReviewPackageDecision]:
        """List review package decisions."""

        status_filter = ReviewDecisionStatus(status) if status else None
        return ReviewPackageDecisionStore(self.store.path).list(scenario_id=scenario_id, status=status_filter)

    def review_package_decision_for_package(self, package_id: str) -> ReviewPackageDecision:
        """Return the latest review decision for one review package."""

        decision = ReviewPackageDecisionStore(self.store.path).get_by_package(package_id)
        if decision is None:
            raise ValueError(f"Unknown review package decision for package: {package_id}")
        return decision

    def _decide_review_package(
        self,
        decision_id: str,
        status: ReviewDecisionStatus,
        comment: str,
    ) -> ReviewPackageDecision:
        cleaned_comment = comment.strip()
        if not cleaned_comment:
            raise ValueError("Review package decision requires a comment.")
        return ReviewPackageDecisionStore(self.store.path).update_status(decision_id, status, cleaned_comment)

    def _stored_candidates(self, candidate_run_ids: list[str]) -> list[StoredEvidenceRun]:
        candidates: list[StoredEvidenceRun] = []
        for candidate_run_id in candidate_run_ids:
            candidate = self.store.get_run(candidate_run_id)
            if candidate is None:
                raise ValueError(f"Unknown candidate run: {candidate_run_id}")
            candidates.append(candidate)
        return candidates

    def build_visualization(self, run: ExternalWorkflowRun) -> WorkflowVisualization:
        """Build diagnostic workflow map data for one imported run."""

        node_ids = [node.id for node in run.nodes]
        total_nodes = len(node_ids)
        traced_node_ids = self._ordered_unique(event.node_id for event in run.trace if event.node_id in node_ids)
        metric_node_ids = self._ordered_unique(
            event.node_id for event in run.trace if event.node_id in node_ids and event.metrics
        )
        explicit_black_boxes = {
            node.id for node in run.nodes if bool(node.metadata.get("black_box") or node.metadata.get("opaque"))
        }
        black_box_node_ids = [
            node_id for node_id in node_ids if node_id not in traced_node_ids or node_id in explicit_black_boxes
        ]
        error_node_ids = self._ordered_unique(
            event.node_id for event in run.trace if event.node_id in node_ids and (event.error or event.status == "failed")
        )
        node_costs = {
            event.node_id: float(event.cost)
            for event in run.trace
            if event.node_id in node_ids and event.cost is not None
        }
        node_latencies = {
            event.node_id: float(event.duration_ms)
            for event in run.trace
            if event.node_id in node_ids and event.duration_ms is not None
        }
        return WorkflowVisualization(
            workflow_id=run.workflow_id,
            run_id=run.run_id,
            nodes=run.nodes,
            edges=run.edges,
            run_path=traced_node_ids,
            total_nodes=total_nodes,
            traced_node_ids=traced_node_ids,
            metric_node_ids=metric_node_ids,
            black_box_node_ids=black_box_node_ids,
            error_node_ids=error_node_ids,
            trace_coverage=self._coverage(len(traced_node_ids), total_nodes),
            metric_coverage=self._coverage(len(metric_node_ids), total_nodes),
            node_costs=node_costs,
            node_latencies_ms=node_latencies,
        )

    def build_report(
        self,
        run: ExternalWorkflowRun,
        visualization: WorkflowVisualization,
    ) -> EvidenceReport:
        """Build a run-level evidence report before baseline comparison."""

        buckets = self._bucket_metrics(run.metrics, self._registry_for(run))
        recommendation = self._run_recommendation(visualization, run)
        quality = EvidenceQualityGate().evaluate(run, visualization)
        return EvidenceReport(
            workflow_id=run.workflow_id,
            run_id=run.run_id,
            run_kind=run.run_kind.value,
            trace_coverage=visualization.trace_coverage,
            metric_coverage=visualization.metric_coverage,
            black_box_node_ids=visualization.black_box_node_ids,
            business_metrics=buckets[MetricCategory.BUSINESS],
            system_metrics=buckets[MetricCategory.SYSTEM],
            data_quality_metrics=buckets[MetricCategory.DATA_QUALITY],
            recommendation=recommendation,
            summary=self._run_summary(run, visualization, recommendation),
            evidence={
                "node_count": visualization.total_nodes,
                "trace_coverage": visualization.trace_coverage,
                "metric_coverage": visualization.metric_coverage,
                "black_box_node_count": len(visualization.black_box_node_ids),
                "quality": quality.model_dump(mode="json"),
            },
        )

    def compare(self, baseline_run_id: str, candidate_run_id: str) -> EvidenceReport:
        """Compare two stored external workflow runs."""

        baseline = self.store.get_run(baseline_run_id)
        candidate = self.store.get_run(candidate_run_id)
        if baseline is None:
            raise ValueError(f"Unknown baseline run: {baseline_run_id}")
        if candidate is None:
            raise ValueError(f"Unknown candidate run: {candidate_run_id}")
        registry = self._registry_for(candidate.run)
        comparator = MetricComparator(registry)
        comparison = comparator.compare(
            baseline.run.metrics,
            candidate.run.metrics,
            run_kind=RunKind(candidate.run.run_kind.value),
            provenance={
                "baseline_run_id": baseline_run_id,
                "candidate_run_id": candidate_run_id,
                "sample_count": candidate.run.metrics.get("sample_count", 0),
                "data_source": candidate.run.metadata.get("data_source"),
            },
        )
        evaluation = EvidenceEvaluationEngine().evaluate(comparison)
        recommendation = self._comparison_recommendation(evaluation.decision)
        report = EvidenceReport(
            workflow_id=candidate.run.workflow_id,
            baseline_run_id=baseline_run_id,
            candidate_run_id=candidate_run_id,
            run_kind=candidate.run.run_kind.value,
            trace_coverage=candidate.visualization.trace_coverage,
            metric_coverage=candidate.visualization.metric_coverage,
            black_box_node_ids=candidate.visualization.black_box_node_ids,
            business_metrics=candidate.report.business_metrics,
            system_metrics=candidate.report.system_metrics,
            data_quality_metrics=candidate.report.data_quality_metrics,
            comparison=comparison,
            recommendation=recommendation,
            summary=(
                f"Candidate {candidate_run_id} vs baseline {baseline_run_id}: "
                f"{comparison.summary} Evidence decision={evaluation.decision.value}; "
                f"recommendation={recommendation.value}."
            ),
            evidence={
                "evaluation": {
                    "decision": evaluation.decision.value,
                    "recommended_action": evaluation.recommended_action.value,
                    "confidence": evaluation.confidence,
                    "reason": evaluation.reason,
                },
                "quality": candidate.report.evidence.get("quality", {}),
                "baseline_run_id": baseline_run_id,
                "candidate_run_id": candidate_run_id,
            },
        )
        self.store.save_comparison_report(report)
        return report

    def export_comparison_markdown(self, baseline_run_id: str, candidate_run_id: str) -> str:
        """Export a human-readable baseline-vs-candidate comparison report."""

        report = self.store.get_comparison_report(baseline_run_id, candidate_run_id)
        if report is None:
            report = self.compare(baseline_run_id, candidate_run_id)
        comparison = report.comparison
        lines = [
            "# Baseline vs Candidate",
            "",
            f"Workflow: {report.workflow_id}",
            f"Baseline: {baseline_run_id}",
            f"Candidate: {candidate_run_id}",
            f"Recommendation: {report.recommendation.value}",
            "",
            "## Summary",
            report.summary,
            "",
            "## Business Metrics",
        ]
        for name, value in report.business_metrics.items():
            diff = comparison.business_metric_diffs.get(name) if comparison else None
            suffix = "" if diff is None else f" (diff {diff:+.4f})"
            lines.append(f"- {name}: {value}{suffix}")
        lines.extend(["", "## System Metrics"])
        for name, value in report.system_metrics.items():
            diff = comparison.system_metric_diffs.get(name) if comparison else None
            suffix = "" if diff is None else f" (diff {diff:+.4f})"
            lines.append(f"- {name}: {value}{suffix}")
        lines.extend(["", "## Evidence"])
        lines.append(f"- Trace coverage: {report.trace_coverage:.0%}")
        lines.append(f"- Metric coverage: {report.metric_coverage:.0%}")
        lines.append(f"- Black boxes: {', '.join(report.black_box_node_ids) or 'none'}")
        return "\n".join(lines)

    @staticmethod
    def _ordered_unique(values: Any) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)
        return result

    @staticmethod
    def _coverage(count: int, total: int) -> float:
        if total <= 0:
            return 1.0
        return round(count / total, 4)

    @staticmethod
    def _registry_for(run: ExternalWorkflowRun) -> MetricSchemaRegistry:
        schemas: list[MetricSchema] = []
        for name, raw_schema in run.metric_schema.items():
            if not isinstance(raw_schema, dict):
                continue
            schemas.append(
                MetricSchema(
                    name=name,
                    direction=MetricDirection(raw_schema.get("direction", "higher")),
                    category=MetricCategory(raw_schema.get("category", "business")),
                    weight=float(raw_schema.get("weight", 1.0)),
                    threshold=raw_schema.get("threshold"),
                    is_guardrail=bool(raw_schema.get("is_guardrail", False)),
                )
            )
        return MetricSchemaRegistry(schemas) if schemas else MetricSchemaRegistry.default_quant()

    @staticmethod
    def _bucket_metrics(
        metrics: dict[str, float],
        registry: MetricSchemaRegistry,
    ) -> dict[MetricCategory, dict[str, float]]:
        buckets: dict[MetricCategory, dict[str, float]] = {
            MetricCategory.BUSINESS: {},
            MetricCategory.SYSTEM: {},
            MetricCategory.DATA_QUALITY: {},
        }
        for name, value in metrics.items():
            category = registry.schema_for(name).category
            if category == MetricCategory.SYSTEM:
                buckets[MetricCategory.SYSTEM][name] = value
            elif category == MetricCategory.DATA_QUALITY:
                buckets[MetricCategory.DATA_QUALITY][name] = value
            else:
                buckets[MetricCategory.BUSINESS][name] = value
        return buckets

    @staticmethod
    def _run_recommendation(
        visualization: WorkflowVisualization,
        run: ExternalWorkflowRun,
    ) -> DecisionRecommendation:
        if visualization.error_node_ids:
            return DecisionRecommendation.REJECT
        if visualization.black_box_node_ids or visualization.trace_coverage < 1.0:
            return DecisionRecommendation.CONTINUE_SHADOW
        if not run.metrics:
            return DecisionRecommendation.INCONCLUSIVE
        return DecisionRecommendation.CONTINUE_SHADOW

    @staticmethod
    def _comparison_recommendation(decision: EvidenceDecision) -> DecisionRecommendation:
        if decision == EvidenceDecision.IMPROVED:
            return DecisionRecommendation.APPROVE
        if decision == EvidenceDecision.WORSE:
            return DecisionRecommendation.REJECT
        return DecisionRecommendation.INCONCLUSIVE

    @staticmethod
    def _run_summary(
        run: ExternalWorkflowRun,
        visualization: WorkflowVisualization,
        recommendation: DecisionRecommendation,
    ) -> str:
        return (
            f"Run {run.run_id} imported for workflow {run.workflow_id}; "
            f"trace_coverage={visualization.trace_coverage:.2f}, "
            f"metric_coverage={visualization.metric_coverage:.2f}, "
            f"black_box_nodes={len(visualization.black_box_node_ids)}, "
            f"recommendation={recommendation.value}."
        )

    @staticmethod
    def _load_payload(path: str | Path) -> dict[str, Any]:
        payload_path = Path(path)
        raw = payload_path.read_text(encoding="utf-8")
        if payload_path.suffix.lower() in {".yaml", ".yml"}:
            try:
                import yaml  # type: ignore[import-untyped]
            except ImportError as exc:
                raise ValueError("YAML workflow import requires PyYAML to be installed.") from exc
            loaded = yaml.safe_load(raw)
        else:
            loaded = json.loads(raw)
        if not isinstance(loaded, dict):
            raise ValueError("Workflow import file must contain a JSON/YAML object.")
        return loaded

    @staticmethod
    def _is_quant_payload(payload: dict[str, Any]) -> bool:
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, dict):
            return False
        contract = str(metadata.get("contract", "")).lower()
        data_source = str(metadata.get("data_source", "")).lower()
        domain = str(metadata.get("domain", "")).lower()
        return contract == "quant_evidence_v1" or data_source == "csv_import" or domain == "quant_strict"
