# A-Share Data Samples

This folder is for local A-share historical data exports used by Loop Harness.

Do not commit private, paid, broker, account, or licensed raw data unless you
have the right to publish it. For normal use, keep real CSV files local and only
commit the manifest shape or sanitized examples.

## Structure

```text
examples/a_share_data/
├── manifest.example.json
├── daily/
│   └── <ts_code>.csv
└── reports/
```

## Required CSV Columns

```text
ts_code
trade_date
open
high
low
close
vol
```

Recommended:

```text
amount
```

`trade_date` supports `YYYYMMDD` and `YYYY-MM-DD`.

## Batch Command

```bash
loopharness evidence quant-a-share-batch \
  --manifest examples/a_share_data/manifest.json \
  --fast-windows 5,10,20 \
  --slow-windows 20,60,120
```

The batch command writes evidence runs to the configured SQLite database and
prints JSON containing:

- quality summary
- recommendation distribution
- best candidate per symbol
- chart payload for ranking and heatmaps
- Markdown report
