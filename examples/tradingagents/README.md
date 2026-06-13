# TradingAgents Export Samples

This folder is the local intake area for operator-provided TradingAgents export samples.

Do not commit real private exports here unless they have been sanitized. Samples must not contain:

- Broker credentials
- API keys or provider secrets
- Private account identifiers
- Personal contact or payment data
- Live trading order IDs
- Any data you do not have permission to store in this repository

## Minimum Sample Gate

Before Loop Harness should build a formal TradingAgents execution adapter, collect:

- Minimum: 5 historical exports
- Preferred: 10 or more historical exports
- Each export should include role trace, strategy config, numeric metrics, artifacts, and run metadata

Fixture-only exports are useful for testing the converter, but they are not decision-grade evidence.

## Manifest Format

Create a local manifest such as `manifest.local.json` next to your samples:

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

`contains_private_data` must be `false` before a sample is committed. Private samples should stay local.
