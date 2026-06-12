"""Evidence gap reporting for imported workflows."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from loop_harness.evidence.models import StoredEvidenceRun


class EvidenceGap(BaseModel):
    """One missing or weak evidence point."""

    code: str
    severity: str
    message: str
    node_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class EvidenceGapReport(BaseModel):
    """Human-facing evidence gap report."""

    workflow_id: str
    run_id: str
    status: str
    gaps: list[EvidenceGap]
    black_box_node_ids: list[str]
    missing_metric_node_ids: list[str]
    missing_trace_node_ids: list[str]
    summary: str


def build_gap_report(stored: StoredEvidenceRun) -> EvidenceGapReport:
    """Build a gap report for one run."""

    gaps: list[EvidenceGap] = []
    node_ids = [node.id for node in stored.run.nodes]
    traced = set(stored.visualization.traced_node_ids)
    metric_nodes = set(stored.visualization.metric_node_ids)
    black_boxes = set(stored.visualization.black_box_node_ids)
    missing_trace = [node_id for node_id in node_ids if node_id not in traced]
    missing_metrics = [node_id for node_id in node_ids if node_id not in metric_nodes]
    for node_id in sorted(black_boxes, key=node_ids.index):
        gaps.append(
            EvidenceGap(
                code="node.black_box",
                severity="warning",
                node_id=node_id,
                message=f"Node {node_id} is not fully observable.",
            )
        )
    for node_id in missing_trace:
        severity = "warning" if node_id in black_boxes else "error"
        gaps.append(
            EvidenceGap(
                code="node.trace_missing",
                severity=severity,
                node_id=node_id,
                message=f"Node {node_id} has no trace event.",
            )
        )
    for metric_name in stored.run.metrics:
        if metric_name not in stored.run.metric_schema:
            gaps.append(
                EvidenceGap(
                    code="metric.schema_missing",
                    severity="warning",
                    message=f"Metric {metric_name} has no schema direction/category.",
                    details={"metric": metric_name},
                )
            )
    if any(gap.severity == "error" for gap in gaps):
        status = "rejected"
    elif gaps:
        status = "warning"
    else:
        status = "accepted"
    return EvidenceGapReport(
        workflow_id=stored.run.workflow_id,
        run_id=stored.run.run_id,
        status=status,
        gaps=gaps,
        black_box_node_ids=stored.visualization.black_box_node_ids,
        missing_metric_node_ids=missing_metrics,
        missing_trace_node_ids=missing_trace,
        summary=(
            f"Run {stored.run.run_id} has {len(gaps)} evidence gaps; "
            f"status={status}."
        ),
    )
