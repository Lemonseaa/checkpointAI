# TradingAgents Research Layer Plan

TradingAgents should be used as a quant research team, not as the source of
truth for execution or approval.

## Positioning

```text
TradingAgents-style team -> StrategyProposal
JoinQuant / RQAlpha       -> historical backtest execution
Loop Harness              -> evidence ingestion, comparison, charts, approval
Human                     -> capital deployment decision
```

This keeps each system in the place where it is strongest.

## What TradingAgents Should Do

TradingAgents can help with:

1. Reading market context and strategy notes.
2. Proposing a small set of strategy hypotheses.
3. Explaining why a candidate deserves a historical test.
4. Interpreting imported JoinQuant/RQAlpha evidence.
5. Suggesting the next controlled parameter range.

TradingAgents should output `StrategyProposal`, not direct trading orders.

## What TradingAgents Must Not Do

TradingAgents must not:

1. Download unlicensed data silently.
2. Run hidden backtests without export artifacts.
3. Treat fixture or synthetic results as decision-grade evidence.
4. Approve paper trading or live trading by itself.
5. Rewrite Loop Harness policy, metric schema, or approval gates.

## StrategyProposal Boundary

Every proposal must include:

```text
hypothesis
strategy_type
universe
parameters
reason
expected_metric
risk_constraints
run_kind
```

The proposal is then converted into a platform config draft:

```text
StrategyProposal
  -> JoinQuant config draft
  -> external backtest
  -> Quant Platform Export Contract
  -> Loop Harness evidence import
```

## First Useful Loop

The first loop should be narrow:

1. Human chooses A-share universe and baseline.
2. TradingAgents proposes 3-5 moving-average or momentum candidates.
3. Loop Harness converts each proposal into JoinQuant/RQAlpha config drafts.
4. External platform runs historical backtests.
5. Loop Harness imports export directories.
6. Loop Harness compares equity, drawdown, Sharpe, return, turnover, and sample count.
7. Human reviews the paper-trading discussion.

## Output Contract For TradingAgents

TradingAgents output should be a JSON object matching the StrategyProposal
contract. Prose can be attached as metadata, but the executable part must stay
structured.

Example:

```json
{
  "scenario_id": "quant_a_share",
  "hypothesis": "A shorter fast moving average may capture medium-term trend changes earlier.",
  "strategy_type": "moving_average_crossover",
  "universe": ["600519.SH", "510300.SH"],
  "parameters": {
    "fast_window": 5,
    "slow_window": 20
  },
  "reason": "The baseline buy-and-hold drawdown is high, so a trend filter is worth testing.",
  "expected_metric": "sharpe",
  "risk_constraints": {
    "max_drawdown": 0.2,
    "min_sample_count": 120
  },
  "run_kind": "historical"
}
```

## Why This Is Better Than Direct Adapter Execution

Directly executing TradingAgents too early would mix research, data access,
backtesting, and approval into one black box. The proposal-first design makes
the loop inspectable:

```text
Why test it?        -> hypothesis + reason
What changed?       -> strategy_type + parameters
What should improve?-> expected_metric
How risky is it?    -> risk_constraints + later policy checks
Did it improve?     -> imported external evidence
```

This is the right place for Loop Harness to add value.
