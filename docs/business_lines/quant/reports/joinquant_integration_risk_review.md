# JoinQuant Integration Risk Review

## Scope

This review covers the current JoinQuant export-import path for the A-share
quant business line.

Loop Harness currently imports JoinQuant-style export directories. It does not
call JoinQuant APIs, place orders, or run live trading.

## Current Strengths

1. Export directories are validated before batch import.
2. Batch import avoids partial evidence writes when one export is broken.
3. Equity and drawdown curves are preserved for visual review.
4. Metrics are compared through the existing evidence and chart layer.
5. Paper-trading discussion is separated from live-trading approval.

## Open Risks

### Data Authorization

Real JoinQuant/JQData exports may be licensed. Loop Harness must not commit or
redistribute licensed raw data without permission.

### Survivorship Bias

A universe chosen after knowing winners can make historical results look better
than they are. Every batch should preserve the original universe selection
reason.

### Adjustment Mode

Backtests must record whether prices are forward-adjusted, backward-adjusted,
or unadjusted. Mixed adjustment modes invalidate comparisons.

### Fees And Slippage

Commission and slippage must be explicit. A candidate that wins only because it
uses cheaper assumptions is not comparable to baseline.

### Overfitting

Parameter grids can fit historical noise. Repeated candidates should be tracked
as experiments, not treated as independent proof.

### Execution Gap

Historical backtest evidence is weaker than paper evidence. Paper evidence is
weaker than live execution evidence. The run kind must remain visible in every
report.

### Platform Export Drift

JoinQuant export formats can change. `joinquant-validate` should be run before
batch import whenever platform export scripts change.

## Current Decision

Status: `usable_for_historical_review`

Reason: the import path can evaluate real exported evidence, but it still
depends on operator-provided data quality, platform assumptions, and human
review before paper-trading discussion.

Not approved for:

```text
automatic paper trading
automatic live trading
broker integration
capital deployment
```
