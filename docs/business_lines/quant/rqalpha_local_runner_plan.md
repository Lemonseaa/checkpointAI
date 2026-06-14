# RQAlpha Local Runner Plan

RQAlpha is the preferred local execution candidate after JoinQuant export import.
Loop Harness should not become the backtest engine; it should run or observe
RQAlpha, then convert outputs into the Quant Platform Export Contract.

## Target Role

```text
RQAlpha = local repeatable backtest runner
Loop Harness = evidence ingestion, comparison, charting, approval
TradingAgents = research hypothesis and result interpretation
```

## Proposed Folder Shape

```text
examples/rqalpha_runs/
├── strategies/
│   └── ma_cross.py
├── configs/
│   └── ma_cross_600519.yml
└── exports/
    └── ma_cross_600519/
        ├── metadata.json
        ├── metrics.json
        ├── equity_curve.csv
        ├── trades.csv
        ├── positions.csv
        └── logs.txt
```

## Runner Responsibilities

1. Accept a strategy file and config file.
2. Run RQAlpha locally through a subprocess.
3. Write outputs to an export directory.
4. Convert RQAlpha artifacts into:

```text
metadata.json
metrics.json
equity_curve.csv
trades.csv
positions.csv
logs.txt
```

5. Hand the export directory to the same platform export importer used by JoinQuant.

## Required Decisions Before Implementation

- Which data bundle will RQAlpha use for A-share data?
- Is the data local and licensed?
- Where will strategy files live?
- Which config fields are allowed to vary automatically?
- What is the minimum sample length before a run can be considered historical evidence?

## Explicit Non-Goals

- No live trading.
- No broker account integration.
- No hidden data download.
- No automatic strategy deployment.
- No replacing JoinQuant or vendor platforms.

## Acceptance Criteria For Future Implementation

- One local RQAlpha run creates a complete Quant Platform Export directory.
- Export quality gate passes only when benchmark, fees, slippage, equity curve,
  trades, positions, and strategy parameters exist.
- Loop Harness can compare an RQAlpha candidate against a baseline using the
  same evidence path as JoinQuant exports.
