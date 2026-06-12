# Workflow Contract v1

Loop Harness does not need to own the workflow runtime. It needs external
workflows to expose enough structure to be inspected, compared, and improved.

This contract defines the minimum shape an external workflow run must provide.

## Required Top-Level Shape

```json
{
  "run_id": "quant_candidate_001",
  "workflow_id": "quant_research_demo",
  "scenario_id": "quant",
  "run_kind": "historical",
  "nodes": [],
  "edges": [],
  "trace": [],
  "metrics": {},
  "metric_schema": {},
  "config": {},
  "artifacts": []
}
```

## Required Fields

`run_id`: unique id for one execution. It must be stable enough to query later.

`workflow_id`: stable id for the workflow being evaluated. Baselines are pinned per workflow.

`scenario_id`: optimization domain, such as `quant`, `content_growth`, or `demo`.

`run_kind`: one of `synthetic`, `historical`, `paper`, or `live`.

`nodes` and `edges`: structural map of the workflow.

```json
{
  "nodes": [
    {
      "id": "researcher",
      "name": "Researcher",
      "type": "agent",
      "metadata": {
        "optimizable": true
      }
    }
  ],
  "edges": [
    {
      "source": "researcher",
      "target": "risk_manager"
    }
  ]
}
```

`trace`: ordered execution evidence. Each trace item should identify the node,
input summary, output summary, timing, status, and optional tool calls.

```json
{
  "node_id": "researcher",
  "status": "succeeded",
  "started_at": "2026-06-12T10:00:00Z",
  "ended_at": "2026-06-12T10:00:05Z",
  "input_summary": "AAPL factor research request",
  "output_summary": "Momentum factor candidate",
  "tool_calls": [
    {
      "name": "backtest",
      "status": "succeeded"
    }
  ]
}
```

`metrics`: named values used for comparison. Each metric should be interpretable
through a metric schema: direction, category, weight, and threshold.

```json
{
  "sharpe": 1.2,
  "max_drawdown": 0.08,
  "sample_count": 120,
  "latency_ms": 3500
}
```

`metric_schema`: optional but strongly recommended. Without it, Loop Harness can
make safe guesses for common system/data-quality metrics, but the result is less
trustworthy.

```json
{
  "sharpe": { "direction": "higher", "category": "business", "weight": 0.7 },
  "max_drawdown": {
    "direction": "lower",
    "category": "guardrail",
    "weight": 0.3,
    "threshold": 0.2,
    "is_guardrail": true
  },
  "latency_ms": { "direction": "lower", "category": "system", "weight": 0.0 }
}
```

`config`: configurable surface that produced the run. This can include prompt
versions, model settings, strategy parameters, tool policy, or workflow version.

`artifacts`: pointers or summaries for reports, charts, logs, generated files,
or backtest result files.

## Structured Output Requirement

External adapters should return structured output rather than raw text whenever
possible. A human-readable answer is useful, but it is not enough for evidence.

Recommended output shape:

```json
{
  "answer": "Candidate strategy improved Sharpe but increased turnover.",
  "metrics": {
    "sharpe": 1.31,
    "max_drawdown": 0.11,
    "turnover": 0.48
  },
  "value_summary": "Sharpe improved from baseline while guardrails stayed valid.",
  "trace": [],
  "artifacts": []
}
```

If an adapter can only return unstructured text, Loop Harness should mark the
run as low observability and avoid optimization recommendations until metrics
and trace are added.

## Optional But Strongly Recommended Fields

- `baseline_run_id`
- `cost`
- `errors`
- `data_quality`
- `human_context`

## Minimum Adapter Output

An adapter is acceptable when it can produce:

1. A stable `run_id`.
2. A stable `workflow_id`.
3. At least two workflow nodes, or a clearly marked single-node workflow.
4. Trace entries for executed nodes.
5. At least one business metric.
6. A declared `run_kind`.
7. Config surface, or explicit explanation that the workflow is observation-only.

## Adapter SDK Shape

The minimum adapter surface is intentionally small:

```python
class WorkflowAdapterSDK:
    def describe_workflow(self) -> dict: ...
    def run(self, payload: dict) -> dict: ...
    def export_trace(self, run_id: str) -> list[dict]: ...
    def export_metrics(self, run_id: str) -> dict[str, float]: ...
```

Adapters can be subprocess, API, or in-process wrappers. The important part is
not how they run. The important part is whether they can export contract-shaped
evidence.

## Rejection Conditions

Reject or mark as low-value when:

- No structured trace is available.
- No business metric is available.
- The workflow is fully black-box and exposes no configurable surface.
- Metrics are not comparable across baseline and candidate.
- `run_kind` is missing.
- The adapter silently fabricates evidence instead of marking data as synthetic.
- The run cannot be linked to a scenario.

## Gap Report

Every ingested run should be able to produce a gap report. The gap report is the
bridge between workflow visualization and optimization readiness.

It should answer:

```text
Which nodes are black boxes?
Which nodes have no trace?
Which nodes produce no metrics?
Which metrics have no schema?
Which parts are observable but not optimizable?
What evidence must be added before recommendations are trustworthy?
```

Optimization is blocked when critical gaps prevent baseline/candidate
comparison. The correct fix is better instrumentation in the external workflow,
not a more aggressive optimizer.

## Evidence Strength

| Evidence | Allowed Use |
|---|---|
| synthetic | UI, plumbing, demo, weak proposals |
| historical | baseline/candidate comparison, cautious recommendation |
| paper | stronger recommendation, still approval-gated |
| live | reporting and rollback evidence, never blind automation |

## Design Rule

If an external workflow cannot satisfy this contract, Loop Harness should not
try to optimize it. First improve the workflow's observability; then compare
changes.

## Related API Surface

```text
POST /api/evidence/contracts/validate
GET  /api/evidence/workflows/{workflow_id}/map
GET  /api/evidence/workflows/{workflow_id}/graph
GET  /api/evidence/runs/{run_id}/graph
GET  /api/evidence/runs/{run_id}/gaps
GET  /api/evidence/runs/{run_id}/nodes/{node_id}
POST /api/evidence/metrics/{scenario_id}
GET  /api/evidence/metrics/{scenario_id}
POST /api/evidence/goals/{scenario_id}
GET  /api/evidence/goals/{scenario_id}
GET  /api/evidence/decision-memory/{scenario_id}
POST /api/evidence/compare/export
```

The `graph` endpoints are the preferred product surface for UI workflow
visualization. They preserve the raw workflow structure but add deterministic
layout, filter buckets, metric-source attribution, evidence gaps, and proposal
target metadata.
