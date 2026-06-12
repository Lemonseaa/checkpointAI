# Charts API

Charts are a core evidence surface. They are not decorative UI.

Loop Harness should use charts to make optimization claims inspectable:

```text
baseline vs candidate
metric trend
guardrail movement
cost and latency movement
evidence quality
```

## Design Rule

The backend owns metric interpretation. The frontend owns rendering.

Frontend code should not decide whether Sharpe is better when higher, drawdown
is better when lower, or sample count is a data-quality metric. Those decisions
come from `MetricSchema` and evidence comparison reports.

## Chart Payload Types

### Optimization Chart

Used when one baseline is compared with multiple candidates.

```json
{
  "workflow_id": "quant_research_demo",
  "scenario_id": "quant",
  "baseline_run_id": "baseline_001",
  "baseline_metrics": {},
  "candidate_points": [],
  "metric_trends": [],
  "chart_fields": ["total_return", "sharpe", "max_drawdown", "objective_score"],
  "guardrail_summary": "No candidates violated configured guardrails.",
  "best_candidate_run_id": "candidate_003",
  "summary": "Baseline compared with 30 candidates."
}
```

### Candidate Point

Each point must include enough context to explain why it is good, weak, or
blocked:

```json
{
  "run_id": "candidate_003",
  "run_kind": "historical",
  "sharpe": 1.31,
  "max_drawdown": 0.11,
  "objective_score": 0.42,
  "guardrail_status": "ok",
  "candidate_quality": "candidate",
  "best_candidate": true,
  "summary": "candidate_003 improved Sharpe without drawdown violation."
}
```

### Metric Trend Point

Trend points are long-form rows so the UI can render line, bar, or scatter
charts without changing the API:

```json
{
  "run_id": "candidate_003",
  "metric": "sharpe",
  "value": 1.31,
  "role": "candidate"
}
```

## Required Views

The console should support these views before adding complex charting:

1. Baseline vs best candidate.
2. All candidates scatter/bar view.
3. Guardrail violations highlighted.
4. Weak candidates visible, not hidden.
5. Cost and latency movement visible when present.

For quant evidence, the first view should show:

```text
baseline total_return  -> best candidate total_return
baseline sharpe        -> best candidate sharpe
baseline max_drawdown  -> best candidate max_drawdown
```

The UI may render these as compact bars, but the interpretation still comes
from backend metric schema and comparison reports.

## Anti-Pattern

Do not show only the winning candidate.

A serious optimization console must also show:

- failed candidates
- weak candidates
- guardrail-breaking candidates
- inconclusive candidates
- candidates with insufficient evidence

Otherwise the system trains humans to trust cherry-picked results.
