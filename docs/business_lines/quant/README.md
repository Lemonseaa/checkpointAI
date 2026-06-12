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

## Reports

Historical drill and acceptance reports live in [reports/](reports/). They are audit records, not the active roadmap.
