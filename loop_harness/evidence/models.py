"""Contracts for external workflow evidence ingestion."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from loop_harness.metrics import ComparisonResult


class EvidenceRunKind(str, Enum):
    """Source type for one external workflow run."""

    FIXTURE = "fixture"
    SYNTHETIC = "synthetic"
    HISTORICAL = "historical"
    PAPER = "paper"
    LIVE = "live"


class DecisionRecommendation(str, Enum):
    """Human-facing recommendation generated from available evidence."""

    APPROVE = "approve"
    REJECT = "reject"
    CONTINUE_SHADOW = "continue_shadow"
    ROLLBACK = "rollback"
    INCONCLUSIVE = "inconclusive"


class WorkflowNode(BaseModel):
    """One node in an imported workflow."""

    id: str
    name: str | None = None
    type: str = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdge(BaseModel):
    """One directed edge in an imported workflow."""

    source: str
    target: str
    type: str = "control"
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceEvent(BaseModel):
    """One observed node execution."""

    node_id: str
    status: str = "unknown"
    duration_ms: float | None = None
    cost: float | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metrics", mode="before")
    @classmethod
    def _numeric_metrics(cls, value: Any) -> dict[str, float]:
        if not isinstance(value, dict):
            return {}
        metrics: dict[str, float] = {}
        for key, metric_value in value.items():
            if isinstance(metric_value, int | float):
                metrics[str(key)] = float(metric_value)
        return metrics


class ArtifactRef(BaseModel):
    """External artifact produced by a workflow run."""

    type: str
    path: str | None = None
    uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExternalWorkflowRun(BaseModel):
    """Normalized external workflow run input."""

    workflow_id: str
    run_id: str
    scenario_id: str = "default"
    run_kind: EvidenceRunKind = EvidenceRunKind.SYNTHETIC
    started_at: str | None = None
    finished_at: str | None = None
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)
    trace: list[TraceEvent] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    metric_schema: dict[str, dict[str, Any]] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metrics", mode="before")
    @classmethod
    def _numeric_metrics(cls, value: Any) -> dict[str, float]:
        if not isinstance(value, dict):
            return {}
        metrics: dict[str, float] = {}
        for key, metric_value in value.items():
            if isinstance(metric_value, int | float):
                metrics[str(key)] = float(metric_value)
        return metrics


class WorkflowVisualization(BaseModel):
    """Diagnostic visualization data for an imported workflow."""

    workflow_id: str
    run_id: str
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    run_path: list[str]
    total_nodes: int
    traced_node_ids: list[str]
    metric_node_ids: list[str]
    black_box_node_ids: list[str]
    error_node_ids: list[str]
    trace_coverage: float
    metric_coverage: float
    node_costs: dict[str, float] = Field(default_factory=dict)
    node_latencies_ms: dict[str, float] = Field(default_factory=dict)


class EvidenceReport(BaseModel):
    """Decision-oriented report for one run or one baseline/candidate comparison."""

    workflow_id: str
    run_id: str | None = None
    baseline_run_id: str | None = None
    candidate_run_id: str | None = None
    run_kind: str
    trace_coverage: float
    metric_coverage: float
    black_box_node_ids: list[str] = Field(default_factory=list)
    business_metrics: dict[str, float] = Field(default_factory=dict)
    system_metrics: dict[str, float] = Field(default_factory=dict)
    data_quality_metrics: dict[str, float] = Field(default_factory=dict)
    comparison: ComparisonResult | None = None
    recommendation: DecisionRecommendation
    summary: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class IngestResult(BaseModel):
    """Result returned after one ingest operation."""

    run: ExternalWorkflowRun
    visualization: WorkflowVisualization
    report: EvidenceReport


class StoredEvidenceRun(BaseModel):
    """Persisted external run with derived evidence objects."""

    run: ExternalWorkflowRun
    visualization: WorkflowVisualization
    report: EvidenceReport
