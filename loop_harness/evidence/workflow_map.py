"""Workflow map summaries and node-level evidence views."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from loop_harness.evidence.models import (
    ExternalWorkflowRun,
    StoredEvidenceRun,
    TraceEvent,
    WorkflowNode,
)


class WorkflowMapSummary(BaseModel):
    """Aggregated workflow structure for UI maps and diagnostics."""

    workflow_id: str
    scenario_id: str
    latest_run_id: str
    node_count: int
    edge_count: int
    entry_node_ids: list[str]
    exit_node_ids: list[str]
    observable_node_ids: list[str]
    metric_node_ids: list[str]
    black_box_node_ids: list[str]
    error_node_ids: list[str]
    config_surfaces: list[str]
    trace_coverage: float
    metric_coverage: float
    value_summary: str


class NodeEvidenceDetail(BaseModel):
    """UI-ready evidence detail for one workflow node."""

    workflow_id: str
    run_id: str
    node_id: str
    name: str | None = None
    type: str
    status: str
    input_summary: str | None = None
    output_summary: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    latency_ms: float | None = None
    cost: float | None = None
    error: str | None = None
    black_box: bool = False
    optimizable: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


def build_workflow_map(stored_runs: list[StoredEvidenceRun], workflow_id: str) -> WorkflowMapSummary:
    """Build a summary from the latest stored run for one workflow."""

    if not stored_runs:
        raise ValueError(f"Unknown workflow: {workflow_id}")
    latest = stored_runs[-1]
    run = latest.run
    incoming = {edge.target for edge in run.edges}
    outgoing = {edge.source for edge in run.edges}
    node_ids = [node.id for node in run.nodes]
    entry_nodes = [node_id for node_id in node_ids if node_id not in incoming]
    exit_nodes = [node_id for node_id in node_ids if node_id not in outgoing]
    config_surfaces = _config_surfaces(run)
    return WorkflowMapSummary(
        workflow_id=workflow_id,
        scenario_id=run.scenario_id,
        latest_run_id=run.run_id,
        node_count=len(run.nodes),
        edge_count=len(run.edges),
        entry_node_ids=entry_nodes,
        exit_node_ids=exit_nodes,
        observable_node_ids=latest.visualization.traced_node_ids,
        metric_node_ids=latest.visualization.metric_node_ids,
        black_box_node_ids=latest.visualization.black_box_node_ids,
        error_node_ids=latest.visualization.error_node_ids,
        config_surfaces=config_surfaces,
        trace_coverage=latest.visualization.trace_coverage,
        metric_coverage=latest.visualization.metric_coverage,
        value_summary=(
            f"Workflow {workflow_id} has {len(run.nodes)} nodes, "
            f"{len(latest.visualization.black_box_node_ids)} black boxes, "
            f"trace coverage {latest.visualization.trace_coverage:.0%}."
        ),
    )


def build_node_detail(stored: StoredEvidenceRun, node_id: str) -> NodeEvidenceDetail:
    """Build node-level evidence from one stored run."""

    node = _node_by_id(stored.run.nodes, node_id)
    if node is None:
        raise ValueError(f"Unknown node for run {stored.run.run_id}: {node_id}")
    event = _last_trace_event(stored.run.trace, node_id)
    black_box = node_id in stored.visualization.black_box_node_ids
    metadata = dict(node.metadata)
    return NodeEvidenceDetail(
        workflow_id=stored.run.workflow_id,
        run_id=stored.run.run_id,
        node_id=node_id,
        name=node.name,
        type=node.type,
        status=event.status if event is not None else "unobserved",
        input_summary=event.input_summary if event is not None else None,
        output_summary=event.output_summary if event is not None else None,
        metrics=event.metrics if event is not None else {},
        latency_ms=event.duration_ms if event is not None else None,
        cost=event.cost if event is not None else None,
        error=event.error if event is not None else None,
        black_box=black_box,
        optimizable=bool(metadata.get("optimizable") or node.type in {"agent", "prompt", "strategy"}),
        metadata=metadata,
    )


def _node_by_id(nodes: list[WorkflowNode], node_id: str) -> WorkflowNode | None:
    for node in nodes:
        if node.id == node_id:
            return node
    return None


def _last_trace_event(trace: list[TraceEvent], node_id: str) -> TraceEvent | None:
    result: TraceEvent | None = None
    for event in trace:
        if event.node_id == node_id:
            result = event
    return result


def _config_surfaces(run: ExternalWorkflowRun) -> list[str]:
    surfaces: list[str] = []
    seen: set[str] = set()
    for key in run.config:
        seen.add(str(key))
        surfaces.append(str(key))
    for node in run.nodes:
        raw = node.metadata.get("config_surface")
        if isinstance(raw, str) and raw not in seen:
            seen.add(raw)
            surfaces.append(raw)
    return surfaces
