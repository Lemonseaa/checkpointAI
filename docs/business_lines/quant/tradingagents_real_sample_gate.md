# TradingAgents Real Sample Gate

TradingAgents is a candidate external workflow. Loop Harness should not execute or modify it until exported evidence proves that the adapter contract is stable.

## Why This Gate Exists

The current TradingAgents-like sample is a fixture. It proves that a JSON export can be converted into Workflow Contract v1, but it does not prove:

- Real TradingAgents runs expose stable role traces
- Metrics are consistently numeric and comparable
- Strategy config can be captured reliably
- Artifacts are linkable and useful
- Prompt or config control surfaces are available

## Entry Criteria

Formal adapter work can start only after the sample gate has enough evidence:

- At least 5 sanitized historical exports
- 10 or more preferred
- No secrets, credentials, account IDs, or live order IDs
- Every sample has `run_kind=historical`
- Every sample includes `sample_count`, `sharpe`, `max_drawdown`, `total_return`, and `win_rate`
- Every sample exposes at least role-level trace
- Every sample exposes strategy config

## Local Manifest

Use this manifest shape for real samples:

```json
[
  {
    "sample_id": "ta_hist_001",
    "source_path": "examples/tradingagents/ta_hist_001.json",
    "run_kind": "historical",
    "market": "US equities",
    "time_range": "2024-01-01 to 2025-12-31",
    "contains_private_data": false,
    "operator_notes": "Sanitized export with role traces and backtest metrics."
  }
]
```

## Exit Decisions

- `go`: enough real samples, stable contract, adapter can be designed.
- `needs_mapping_fix`: exports are useful, but field mapping must be repaired first.
- `needs_more_samples`: not enough real exports.
- `no_go`: exports cannot expose enough structure for Loop Harness.

Fixture evidence can never produce `go`.
