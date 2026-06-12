# Workflow Visualization Model

Workflow visualization is a diagnostic surface, not a workflow editor.

The UI should render a normalized graph payload produced by Loop Harness. It
should not infer business meaning from raw adapter output.

## Graph Payload

The graph model has five responsibilities:

1. Show the workflow structure.
2. Show the actual run path.
3. Mark black-box and error nodes.
4. Attribute metrics to source nodes.
5. Show where proposals can safely target configuration surfaces.

Minimum payload:

```json
{
  "workflow_id": "quant_research_demo",
  "run_id": "candidate_001",
  "scenario_id": "quant",
  "nodes": [],
  "edges": [],
  "run_path": [],
  "metric_sources": {},
  "filters": {},
  "legend": {},
  "summary": "Graph for quant_research_demo/candidate_001."
}
```

## Node Signals

Each node should expose:

- status
- node type
- layout
- metric names
- artifact references
- black-box flag
- error flag
- high-cost flag
- high-latency flag
- optimizable flag
- evidence gaps

These signals let a human quickly separate:

```text
observable nodes
black-box nodes
expensive nodes
slow nodes
risky nodes
candidate optimization targets
```

## Drawing Rule

The graph should be stable and deterministic. The same workflow should not jump
around between renders unless the structure changes.

Recommended layout:

```text
left to right by dependency depth
top to bottom within each depth
active run path visually emphasized
black-box nodes visually distinct
metric-producing nodes visually distinct
```

## Interaction Rule

Clicking a node should show:

- input summary
- output summary
- trace events
- metrics produced by the node
- artifacts
- gaps
- whether the node is eligible for proposal targeting

The UI should not let users edit workflow code or prompts directly from the
graph. Edits must become proposals and evidence packages.

## Black-Box Rule

A node is black-box when it lacks enough evidence to explain its behavior.

Common causes:

- no trace event
- no output summary
- no metric attribution
- no artifact
- failed or missing tool-call record

Black-box nodes are not failures by themselves. They are instrumentation tasks.
Loop Harness should say what evidence is missing before suggesting optimization.
