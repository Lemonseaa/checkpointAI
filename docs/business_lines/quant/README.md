# Quant Business Line

The quant line is the first serious validation path because it has historical data, repeatable backtests, explicit metrics, and a clear paper-trading gate.

## Current Direction

```text
historical data
  -> backtest run
  -> workflow evidence
  -> baseline/candidate comparison
  -> evidence report
  -> paper-trading recommendation
```

## A-Share First Data Path

The first serious market is A-share. Other markets can wait.

Good data matters more than a quick generic demo. The preferred path is:

```text
licensed/vendor A-share export or Tushare Pro
  -> normalized A-share market data contract
  -> baseline/candidate backtest
  -> evidence run
  -> baseline/candidate comparison
  -> chart/report/review package
```

Supported source priorities:

```text
1. vendor-csv: operator-provided licensed export from Tushare Pro, JoinQuant, RiceQuant, Choice, Wind, or broker research platform
2. tushare: explicit-token API bridge, no silent fallback
3. static-a-share: deterministic fixture for tests and demos only
```

Scraped or unstable sources are not the main path for serious evidence. A data
set must preserve source, vendor, license note, adjustment mode, sample count,
and quality flags. Static or fixture data is always marked non-decision-grade.

Run the A-share loop with deterministic demo data:

```bash
loopharness evidence quant-a-share-loop \
  --symbol 600519.SH \
  --provider static-a-share \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --fast-window 5 \
  --slow-window 20
```

Run it with a serious vendor CSV export:

```bash
loopharness evidence quant-a-share-loop \
  --symbol 600519.SH \
  --provider vendor-csv \
  --data-path /path/to/600519_daily.csv \
  --vendor tushare_pro_export \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --adjusted qfq \
  --fast-window 5 \
  --slow-window 20
```

Required market-data CSV columns:

```text
ts_code
trade_date
open
high
low
close
vol
```

Recommended column:

```text
amount
```

Historical A-share backtests can support research and paper-trading discussion.
They still cannot prove live-trading profitability.

## A-Share Batch Experiments

Use a manifest when you have multiple real A-share samples:

```text
examples/a_share_data/
├── manifest.json
├── daily/
│   ├── 600519.SH.csv
│   ├── 000001.SZ.csv
│   └── 510300.SH.csv
└── reports/
```

The manifest owns provenance and quality metadata:

```text
ts_code
name
source_vendor
adjusted_mode
start_date
end_date
decision_grade
license_note
file_path
```

Run a batch parameter grid:

```bash
loopharness evidence quant-a-share-batch \
  --manifest examples/a_share_data/manifest.json \
  --fast-windows 5,10,20 \
  --slow-windows 20,60,120
```

The batch output includes:

```text
quality_summary
recommendation_distribution
best_candidates
chart_payload.symbol_ranking
chart_payload.parameter_heatmap
chart_payload.quality_distribution
chart_payload.drawdown_blockers
markdown
```

This is the first practical path for running 30-50 real historical A-share
experiments before adding more framework features.

## Quant Platform Exports

Loop Harness should not clone platform backtest engines. Serious A-share
research should use external execution platforms and import their evidence.

Platform roles:

```text
Data source: Tushare / JQData / RQData / vendor CSV
Backtest execution: JoinQuant export / RQAlpha local runner
Research suggestions: TradingAgents-style research team
Evidence control: Loop Harness
Paper/live trading: later stage with explicit human approval
```

Standard export directory:

```text
export_dir/
├── metadata.json
├── metrics.json
├── equity_curve.csv
├── trades.csv
├── positions.csv
└── logs.txt
```

`metadata.json` must include:

```text
platform
run_id
strategy_name
strategy_version
universe
benchmark
start_date
end_date
initial_cash
commission
slippage
frequency
run_kind
parameters
```

`metrics.json` must include the quant evidence metrics:

```text
total_return
annual_return
sharpe
max_drawdown
volatility
win_rate
turnover
trade_count
benchmark_return
excess_return
sample_count
```

JoinQuant export batch shape:

```text
examples/joinquant_exports/
├── baseline/
├── ma_5_20/
├── ma_10_60/
└── ma_20_120/
```

JoinQuant export quality gate blocks exports that miss benchmark, fees,
slippage, equity curve, trades, positions, strategy parameters, enough samples,
or supported run kind.

Validate one JoinQuant export without writing to the evidence database:

```bash
loopharness evidence joinquant-validate \
  --export-dir examples/joinquant_exports/ma_5_20
```

Import one JoinQuant export:

```bash
loopharness evidence joinquant-import \
  --export-dir examples/joinquant_exports/ma_5_20 \
  --workflow joinquant_ma \
  --scenario quant_a_share
```

Import a baseline-plus-candidates batch:

```bash
loopharness evidence joinquant-batch \
  --batch-dir examples/joinquant_exports \
  --workflow joinquant_batch \
  --scenario quant_a_share
```

Batch import performs preflight validation before writing any evidence. If one
candidate is structurally invalid or blocked by quality gates, no run in the
batch is stored.

The batch output includes:

```text
baseline_run_id
candidate_run_ids
quality_reports
comparison_reports
chart
curve_payload.equity_curves
curve_payload.drawdown_curves
paper_trading_discussion
markdown
```

RQAlpha local execution is planned in
[rqalpha_local_runner_plan.md](rqalpha_local_runner_plan.md). It should produce
the same Quant Platform Export Contract before Loop Harness ingests it.

## Strategy Proposals

Loop Harness does not directly mutate live trading systems. A quant change
starts as a structured `StrategyProposal`, then becomes an external backtest
config draft.

Supported proposal families:

```text
moving_average_crossover
momentum
mean_reversion
```

Required fields:

```text
scenario_id
hypothesis
strategy_type
universe
parameters
reason
expected_metric
risk_constraints
run_kind
```

`StrategyProposal` can be converted to `joinquant` or `rqalpha` config drafts.
The external platform runs the test and exports evidence back through the Quant
Platform Export Contract.

Convert a proposal JSON file:

```bash
loopharness evidence strategy-proposal-to-config \
  --path proposal.json \
  --platform joinquant
```

TradingAgents should sit before this step as a research layer. It proposes
structured strategy changes; it does not approve deployment or replace the
evidence gate. See
[tradingagents_research_layer_plan.md](tradingagents_research_layer_plan.md).

The current JoinQuant risk review is documented in
[reports/joinquant_integration_risk_review.md](reports/joinquant_integration_risk_review.md).

## Current Drill

```bash
loopharness evidence quant-drill --candidates 30 --comparisons 5
```

This is a deterministic semi-real drill. It validates the evidence chain; it is not a live trading signal.

For pre-V3 hardening, use the V2 drill:

```bash
loopharness evidence quant-drill --v2 --candidates 30 --comparisons 5
```

The V2 drill intentionally includes weak and guardrail-violating candidates.
Its purpose is to verify that charts, comparison reports, and recommendations
show both improvement and rejection evidence instead of only happy-path wins.

## CSV Backtest Import

Use CSV import when an external quant workflow already produced backtest rows:

```bash
loopharness evidence import-quant-csv \
  --path tests/fixtures/quant_backtest_results.csv \
  --workflow csv_quant_workflow \
  --scenario quant \
  --kind historical
```

Required columns:

```text
run_id
fast_window
slow_window
total_return
sharpe
max_drawdown
win_rate
turnover
trade_count
```

Recommended columns:

```text
sample_count
capital
volatility
benchmark_return
excess_return
```

If `sample_count` is missing, the importer uses the historical compatibility
default. Serious paper-trading review should provide the real sample count.

Quant evidence is stricter than generic workflow evidence. It must include:

```text
total_return
sharpe
max_drawdown
win_rate
sample_count
```

`max_drawdown` and `win_rate` must be ratios between 0 and 1. A candidate that
improves return but violates max-drawdown guardrails is rejected or sent back for
refinement; it cannot be recommended for paper trading.

After import, build a visual optimization chart:

```bash
loopharness evidence chart \
  --baseline csv_baseline \
  --candidate csv_candidate_strong \
  --candidate csv_candidate_weak
```

Package the same evidence for human or Hermes review:

```bash
loopharness evidence package \
  --baseline csv_baseline \
  --candidate csv_candidate_strong \
  --candidate csv_candidate_weak
```

For a readable handoff note:

```bash
loopharness evidence package \
  --baseline csv_baseline \
  --candidate csv_candidate_strong \
  --candidate csv_candidate_weak \
  --markdown
```

Submit the package to the human approval inbox:

```bash
loopharness evidence package-submit \
  --path review_package.json \
  --reason "Candidate package is ready for human review."
```

Record the human decision:

```bash
loopharness evidence package-decide \
  --id <decision_id> \
  --approve \
  --comment "Approved for paper review."
```

Historical CSV evidence can support comparison and paper-trading discussion.
It is still not live trading proof. Paper and live stages need separate run
kind labels and stronger execution trace.

Review packages now include a quant decision section that answers:

```text
这次测试了什么策略？
baseline 是什么？
candidate 改了什么？
哪些指标变好？
哪些风险变坏？
是否建议进入 paper trading？
人需要审批什么？
```

## Next Step

R2.1 should connect real historical data through CSV or exported backtest results before adding new framework features.

The first serious external workflow candidate is TradingAgents. The plan is
[tradingagents_adapter_plan.md](tradingagents_adapter_plan.md).

Loop Harness should observe TradingAgents runs, not replace the TradingAgents
team structure.

Before formal TradingAgents adapter work starts, fill the
[TradingAgents go/no-go report](reports/tradingagents_spike_go_no_go.md) with
real sanitized historical exports. Adapter work can start only when the report
says `go`, or `needs_mapping_fix` with explicit mapping fixes.

## Reports

Historical drill and acceptance reports live in [reports/](reports/). They are audit records, not the active roadmap.
