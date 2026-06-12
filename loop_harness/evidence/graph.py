"""Workflow graph payloads for productized evidence visualization."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from pydantic import BaseModel, Field

from loop_harness.evidence.gap import EvidenceGap, build_gap_report
from loop_harness.evidence.models import StoredEvidenceRun


class WorkflowGraphNode(BaseModel):
    """One UI-ready workflow graph node."""

    id: str
    label: str
    node_type: str
    status: str
    layout: dict[str, int]
    metric_names: list[str] = Field(default_factory=list)
    artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    black_box: bool = False
    error: bool = False
    high_cost: bool = False
    high_latency: bool = False
    optimizable: bool = False
    gaps: list[EvidenceGap] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowGraphEdge(BaseModel):
    """One UI-ready workflow graph edge."""

    source: str
    target: str
    edge_type: str = "control"
    active: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowGraphPayload(BaseModel):
    """Complete graph payload consumed by the UI."""

    workflow_id: str
    run_id: str
    scenario_id: str
    nodes: list[WorkflowGraphNode]
    edges: list[WorkflowGraphEdge]
    run_path: list[str]
    metric_sources: dict[str, list[str]]
    filters: dict[str, list[str]]
    legend: dict[str, str]
    summary: str

    def proposal_target_metadata(self, node_id: str, config_surface: str, expected_metric: str) -> dict[str, Any]:
        """Return proposal targeting metadata for one graph node."""

        node = next((item for item in self.nodes if item.id == node_id), None)
        return {
            "target_node_id": node_id,
            "target_node_type": node.node_type if node is not None else "unknown",
            "target_config_surface": config_surface,
            "expected_metric": expected_metric,
            "metric_source_nodes": self.metric_sources.get(expected_metric, []),
        }


class WorkflowGraphBuilder:
    """Build deterministic graph payloads from stored evidence runs."""

    NODE_TYPES = {"agent", "tool", "llm", "human", "data", "external", "output", "strategy", "evaluation", "transform"}

    def build(self, stored: StoredEvidenceRun | None) -> WorkflowGraphPayload:
        """Build one graph payload."""

        if stored is None:
            raise ValueError("Stored evidence run is required")
        run = stored.run
        layout = self._layout(stored)
        metric_sources = self._metric_sources(stored)
        gap_report = build_gap_report(stored)
        gaps_by_node: dict[str, list[EvidenceGap]] = defaultdict(list)
        for gap in gap_report.gaps:
            if gap.node_id:
                gaps_by_node[gap.node_id].append(gap)
        active_edges = set(zip(stored.visualization.run_path, stored.visualization.run_path[1:], strict=False))
        max_cost = max(stored.visualization.node_costs.values(), default=0.0)
        max_latency = max(stored.visualization.node_latencies_ms.values(), default=0.0)
        artifact_by_node: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for artifact in run.artifacts:
            node_id = artifact.metadata.get("node_id")
            if isinstance(node_id, str):
                artifact_by_node[node_id].append(artifact.model_dump(mode="json"))
        nodes: list[WorkflowGraphNode] = []
        for node in run.nodes:
            node_type = node.type if node.type in self.NODE_TYPES else "unknown"
            status = self._status_for(stored, node.id)
            metric_names = sorted(metric for metric, sources in metric_sources.items() if node.id in sources)
            cost = stored.visualization.node_costs.get(node.id, 0.0)
            latency = stored.visualization.node_latencies_ms.get(node.id, 0.0)
            nodes.append(
                WorkflowGraphNode(
                    id=node.id,
                    label=node.name or node.id,
                    node_type=node_type,
                    status=status,
                    layout=layout.get(node.id, {"x": 0, "y": 0}),
                    metric_names=metric_names,
                    artifact_refs=artifact_by_node.get(node.id, []),
                    black_box=node.id in stored.visualization.black_box_node_ids,
                    error=node.id in stored.visualization.error_node_ids,
                    high_cost=max_cost > 0 and cost == max_cost,
                    high_latency=max_latency > 0 and latency == max_latency,
                    optimizable=bool(node.metadata.get("optimizable") or node_type in {"agent", "llm", "strategy"}),
                    gaps=gaps_by_node.get(node.id, []),
                    metadata=node.metadata,
                )
            )
        edges = [
            WorkflowGraphEdge(
                source=edge.source,
                target=edge.target,
                edge_type=edge.type,
                active=(edge.source, edge.target) in active_edges,
                metadata=edge.metadata,
            )
            for edge in run.edges
        ]
        filters = {
            "black_box": [node.id for node in nodes if node.black_box],
            "error": [node.id for node in nodes if node.error],
            "metric": [node.id for node in nodes if node.metric_names],
            "high_cost": [node.id for node in nodes if node.high_cost],
            "high_latency": [node.id for node in nodes if node.high_latency],
        }
        return WorkflowGraphPayload(
            workflow_id=run.workflow_id,
            run_id=run.run_id,
            scenario_id=run.scenario_id,
            nodes=nodes,
            edges=edges,
            run_path=stored.visualization.run_path,
            metric_sources=metric_sources,
            filters=filters,
            legend={
                "black_box": "Node has incomplete observability.",
                "error": "Node has failed trace evidence.",
                "metric": "Node produced at least one metric.",
                "high_cost": "Node has the highest observed cost in this run.",
                "high_latency": "Node has the highest observed latency in this run.",
            },
            summary=(
                f"Graph for {run.workflow_id}/{run.run_id}: {len(nodes)} nodes, "
                f"{len(filters['black_box'])} black boxes, {len(filters['metric'])} metric nodes."
            ),
        )

    @staticmethod
    def _metric_sources(stored: StoredEvidenceRun) -> dict[str, list[str]]:
        sources: dict[str, list[str]] = defaultdict(list)
        for event in stored.run.trace:
            for metric in event.metrics:
                if event.node_id not in sources[metric]:
                    sources[metric].append(event.node_id)
        for metric in stored.run.metrics:
            sources.setdefault(metric, [])
        return dict(sources)

    @staticmethod
    def _status_for(stored: StoredEvidenceRun, node_id: str) -> str:
        status = "unobserved"
        for event in stored.run.trace:
            if event.node_id == node_id:
                status = event.status
        return status

    @staticmethod
    def _layout(stored: StoredEvidenceRun) -> dict[str, dict[str, int]]:
        outgoing: dict[str, list[str]] = defaultdict(list)
        incoming_count = {node.id: 0 for node in stored.run.nodes}
        for edge in stored.run.edges:
            outgoing[edge.source].append(edge.target)
            incoming_count[edge.target] = incoming_count.get(edge.target, 0) + 1
        queue = deque([node.id for node in stored.run.nodes if incoming_count.get(node.id, 0) == 0])
        depth: dict[str, int] = {node_id: 0 for node_id in queue}
        while queue:
            current = queue.popleft()
            for target in outgoing.get(current, []):
                depth[target] = max(depth.get(target, 0), depth[current] + 1)
                incoming_count[target] -= 1
                if incoming_count[target] <= 0:
                    queue.append(target)
        by_depth: dict[int, list[str]] = defaultdict(list)
        for node in stored.run.nodes:
            by_depth[depth.get(node.id, 0)].append(node.id)
        return {
            node_id: {"x": x, "y": y}
            for x, node_ids in by_depth.items()
            for y, node_id in enumerate(node_ids)
        }
