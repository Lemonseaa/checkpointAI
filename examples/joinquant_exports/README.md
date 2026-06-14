# JoinQuant Export Examples

This directory documents the expected local JoinQuant export shape.

Do not commit real licensed market data, account identifiers, broker reports,
live order IDs, API tokens, or private research notes here. Keep real exports in
a local/private path and point Loop Harness to that path.

## Directory Shape

```text
joinquant_exports/
├── baseline/
│   ├── metadata.json
│   ├── metrics.json
│   ├── equity_curve.csv
│   ├── trades.csv
│   ├── positions.csv
│   └── logs.txt
├── ma_5_20/
│   └── ...
└── ma_10_60/
    └── ...
```

## Validate Before Import

Validate one export without writing to the evidence database:

```bash
loopharness evidence joinquant-validate \
  --export-dir /private/path/joinquant_exports/ma_5_20
```

Import a full batch only after validation:

```bash
loopharness evidence joinquant-batch \
  --batch-dir /private/path/joinquant_exports \
  --workflow joinquant_batch \
  --scenario quant_a_share
```

Batch import performs preflight validation before storing evidence. If one
candidate is structurally invalid or blocked by quality gates, no baseline or
candidate run is written.

## Minimum Real-Data Requirements

For paper-trading discussion, each export should include:

```text
benchmark
commission
slippage
strategy parameters
equity curve
trades
positions
sample_count >= 120
run_kind = historical or paper
```

Historical evidence can support discussion. It is not live-trading approval.
