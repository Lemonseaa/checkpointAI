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

After import, build a visual optimization chart:

```bash
loopharness evidence chart \
  --baseline csv_baseline \
  --candidate csv_candidate_strong \
  --candidate csv_candidate_weak
```

Historical CSV evidence can support comparison and paper-trading discussion.
It is still not live trading proof. Paper and live stages need separate run
kind labels and stronger execution trace.

## Next Step

R2.1 should connect real historical data through CSV or exported backtest results before adding new framework features.

The first serious external workflow candidate is TradingAgents. The plan is
[tradingagents_adapter_plan.md](tradingagents_adapter_plan.md).

Loop Harness should observe TradingAgents runs, not replace the TradingAgents
team structure.

## Reports

Historical drill and acceptance reports live in [reports/](reports/). They are audit records, not the active roadmap.
