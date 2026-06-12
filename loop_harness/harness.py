"""Clean Evidence Harness facade.

This is the mainline product entrypoint. It intentionally wraps only evidence
storage and service operations, without constructing the legacy agent runtime,
workflow engine, tool registry, or runtime policy stack.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loop_harness.evidence import (
    EvidenceGapReport,
    EvidenceReport,
    EvidenceService,
    EvidenceStore,
    IngestResult,
    NodeEvidenceDetail,
    OptimizationChartPayload,
    QuantCSVImportResult,
    StoredEvidenceRun,
    WorkflowGraphPayload,
    WorkflowMapSummary,
    WorkflowVisualization,
)


class EvidenceHarness:
    """Small facade for external workflow evidence ingestion and review."""

    def __init__(self, sqlite_path: str | Path) -> None:
        self.store = EvidenceStore(sqlite_path)
        self.service = EvidenceService(self.store)

    def ingest_file(self, path: str | Path) -> IngestResult:
        """Ingest one external workflow run JSON file."""

        return self.service.ingest_file(path)

    def ingest_payload(self, payload: dict[str, Any]) -> IngestResult:
        """Ingest one external workflow run payload."""

        return self.service.ingest_payload(payload)

    def ingest_quant_csv(
        self,
        path: str | Path,
        *,
        workflow_id: str,
        scenario_id: str,
        run_kind: str,
    ) -> QuantCSVImportResult:
        """Import quant backtest CSV rows as evidence runs."""

        return self.service.ingest_quant_csv(
            path,
            workflow_id=workflow_id,
            scenario_id=scenario_id,
            run_kind=run_kind,
        )

    def visualize(self, run_id: str) -> WorkflowVisualization:
        """Return stored visualization data for one run."""

        stored = self.store.get_run(run_id)
        if stored is None:
            raise ValueError(f"Unknown evidence run: {run_id}")
        return stored.visualization

    def report(self, run_id: str) -> EvidenceReport:
        """Return stored evidence report for one run."""

        stored = self.store.get_run(run_id)
        if stored is None:
            raise ValueError(f"Unknown evidence run: {run_id}")
        return stored.report

    def workflow_map(self, workflow_id: str) -> WorkflowMapSummary:
        """Return a workflow-level map summary."""

        return self.service.workflow_map(workflow_id)

    def gap_report(self, run_id: str) -> EvidenceGapReport:
        """Return an evidence gap report for one run."""

        return self.service.gap_report(run_id)

    def node_detail(self, run_id: str, node_id: str) -> NodeEvidenceDetail:
        """Return node-level evidence detail for one run."""

        return self.service.node_detail(run_id, node_id)

    def graph_for_run(self, run_id: str) -> WorkflowGraphPayload:
        """Return graph payload for one run."""

        return self.service.graph_for_run(run_id)

    def graph_for_workflow(self, workflow_id: str) -> WorkflowGraphPayload:
        """Return graph payload for the latest workflow run."""

        return self.service.graph_for_workflow(workflow_id)

    def optimization_chart(self, workflow_id: str) -> OptimizationChartPayload:
        """Return an optimization chart for one workflow."""

        return self.service.optimization_chart(workflow_id)

    def optimization_chart_for_runs(
        self,
        baseline_run_id: str,
        candidate_run_ids: list[str],
    ) -> OptimizationChartPayload:
        """Return an optimization chart for explicit baseline/candidate runs."""

        return self.service.optimization_chart_for_runs(baseline_run_id, candidate_run_ids)

    def compare(self, baseline_run_id: str, candidate_run_id: str) -> EvidenceReport:
        """Compare a candidate run against a baseline run."""

        return self.service.compare(baseline_run_id, candidate_run_id)

    def export_comparison_markdown(self, baseline_run_id: str, candidate_run_id: str) -> str:
        """Export a comparison report as Markdown."""

        return self.service.export_comparison_markdown(baseline_run_id, candidate_run_id)

    def list_runs(self, workflow_id: str | None = None) -> list[StoredEvidenceRun]:
        """List stored evidence runs, optionally scoped by workflow."""

        return self.store.list_runs(workflow_id=workflow_id)
