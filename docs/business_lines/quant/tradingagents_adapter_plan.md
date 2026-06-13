# TradingAgents Adapter Plan

## Goal

Use TradingAgents as the first serious external workflow candidate for Loop
Harness.

The goal is not to clone TradingAgents. The goal is to observe its research
workflow, normalize its runs into Workflow Contract v1, and prove whether
strategy or prompt changes improved backtest outcomes.

## Why TradingAgents First

Quant is the best early validation domain because it has:

- historical data;
- repeatable backtests;
- explicit metrics;
- baseline/candidate comparison;
- paper-trading gate before live deployment.

This makes it easier to prove whether Loop Harness is useful.

## What Loop Harness Should Observe

TradingAgents-style workflows usually contain roles such as:

- market data collector;
- researcher / analyst;
- factor or strategy proposer;
- risk manager;
- backtester;
- final decision maker.

Loop Harness should observe:

1. Which roles ran.
2. What each role received and produced.
3. What tools were called.
4. Which strategy/config/prompt changed.
5. Which backtest metrics changed.
6. Whether the change beat the active baseline.
7. Whether drawdown, turnover, sample size, latency, or cost became worse.

## Minimum Evidence Contract

A TradingAgents adapter is not worth building until one sample run can provide:

- `workflow_id`;
- `run_id`;
- `scenario_id = quant`;
- `run_kind = historical` or `paper`;
- workflow nodes and edges;
- node-level trace;
- strategy config surface;
- prompt/config version identifiers when available;
- business metrics: at least Sharpe, total return, max drawdown;
- data quality metric: sample count or test window length;
- system metric: latency or cost;
- artifacts: backtest report path or URI.

## Output Mapping

| TradingAgents-like field | Loop Harness field | Use |
|---|---|---|
| `run_id` | `run_id` | Stable evidence run identity |
| `workflow_id` | `workflow_id` | Baseline/candidate grouping |
| `run_kind` | `run_kind` | Evidence strength: historical/paper/live |
| `agents[].id` | `nodes[].id` and `trace[].node_id` | Workflow visualization |
| `agents[].role` | `nodes[].name` and trace metadata | Human-readable role map |
| `agents[].input/output` | `trace[].input_summary/output_summary` | Node-level explanation |
| `agents[].duration_ms` | `trace[].duration_ms` | Latency evidence |
| `agents[].cost` | `trace[].cost` | Cost evidence |
| `strategy_config` | `config` | Config surface / candidate change |
| `metrics.sharpe` | `metrics.sharpe` | Business metric |
| `metrics.total_return` | `metrics.total_return` | Business metric |
| `metrics.max_drawdown` | `metrics.max_drawdown` | Guardrail metric |
| `metrics.win_rate` | `metrics.win_rate` | Business metric |
| `metrics.sample_count` | `metrics.sample_count` | Data-quality metric |
| `artifacts[]` | `artifacts[]` | Review package links |

Fields that are only prose remain artifacts or summaries. They must not be
promoted to metrics without numeric extraction.

## Candidate Metrics

| Metric | Direction | Category | Notes |
|---|---|---|---|
| sharpe | higher | business | Primary risk-adjusted return metric. |
| total_return | higher | business | Useful but not sufficient alone. |
| max_drawdown | lower | guardrail | Must not cross risk limit. |
| turnover | lower | guardrail | Controls trading friction. |
| sample_count | higher | data_quality | Reject tiny samples. |
| backtest_days | higher | data_quality | Prefer longer windows. |
| latency_ms | lower | system | Do not optimize at any runtime cost. |
| api_cost | lower | system | Cost is a constraint, not the objective. |

## Adapter Strategy

Phase 1: export-only spike.

- Do not modify TradingAgents deeply.
- Run TradingAgents normally.
- Export one JSON file that matches Workflow Contract v1.
- Ingest it with `loopharness evidence ingest`.

Current spike converter:

```bash
python scripts/business_lines/quant/convert_tradingagents_export.py \
  --input tests/fixtures/tradingagents_like_run.json \
  --output /tmp/tradingagents_evidence.json
```

The converter accepts a TradingAgents-like JSON export and writes Loop Harness
Workflow Contract v1 evidence. It does not run TradingAgents.

Phase 2: baseline/candidate comparison.

- Capture one baseline run.
- Capture at least five candidate runs.
- Compare candidates against the pinned baseline.
- Generate evidence reports.

Phase 3: controlled proposal.

- Create a proposal only when evidence is historical or paper-quality.
- Require human approval before any live trading use.
- Record decision and rollback path.

## What Not To Do

- Do not rewrite TradingAgents inside Loop Harness.
- Do not add live trading automation.
- Do not claim alpha from synthetic fixtures.
- Do not optimize prompts before trace and metrics are reliable.
- Do not add broad adapter abstractions before one export-only spike works.

## Entry Criteria

Start the adapter spike only when:

1. Workflow Contract v1 is stable.
2. Built-in quant demo passes.
3. Compatibility checklist says `needs_spike` or `go`.
4. One TradingAgents run can be executed locally or exported from an existing run.

## Success Criteria

The first useful milestone is:

1. Ingest at least 10 TradingAgents historical runs.
2. Pin one baseline.
3. Compare at least 5 candidates.
4. Show the workflow in Workflow Maps.
5. Generate at least 3 evidence reports.
6. Produce one approve/reject recommendation with clear reasons.
7. Record at least one system limitation discovered from real data.

## Current Spike Decision

Decision: `needs_spike`, not formal adapter yet.

Reason:

- Export-only conversion is feasible with a TradingAgents-like JSON file.
- Loop Harness can ingest the converted payload, compare it against a baseline,
  and generate a review package.
- Formal adapter work still depends on real TradingAgents samples proving stable
  role trace, metrics, config, artifacts, and prompt/config control surfaces.

Next concrete action:

```text
Collect 5-10 real TradingAgents historical exports and run them through the
converter before writing any code that executes TradingAgents directly.
```

## Hard Boundary

Loop Harness decides whether a TradingAgents change is supported by evidence.
It does not decide to deploy capital automatically.
