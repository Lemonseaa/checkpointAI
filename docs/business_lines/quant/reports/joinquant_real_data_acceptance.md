# JoinQuant Real Data Acceptance

This document defines the current acceptance path for real JoinQuant export
batches.

## Goal

Use JoinQuant as the external backtest execution platform, then use Loop Harness
as the evidence, comparison, and review layer.

The command is:

```bash
loopharness evidence joinquant-real-drill \
  --batch-dir /path/to/joinquant_exports \
  --workflow joinquant_real_drill \
  --scenario quant_a_share \
  --normalize-dir /path/to/normalized_exports \
  --output-json /path/to/drill_report.json \
  --output-markdown /path/to/drill_report.md
```

Add `--markdown` when the output is for human review.

For local acceptance without private data:

```bash
python scripts/business_lines/quant/create_joinquant_fixture.py \
  --output-dir /tmp/joinquant_fixture
```

Then run the drill against `/tmp/joinquant_fixture`. This fixture only verifies
the evidence pipeline; it is not market evidence.

## Required Batch Shape

```text
joinquant_exports/
├── baseline/
├── candidate_1/
└── candidate_2/
```

Each run directory must contain:

```text
metadata.json
metrics.json
equity_curve.csv
trades.csv
positions.csv
logs.txt
```

## Drill Sequence

```text
diagnose
  -> sensitive-data scan
  -> optional normalize
  -> validate
  -> batch import
  -> compare candidates with baseline
  -> markdown/json report
```

The drill does not connect to JoinQuant APIs, does not place orders, and does
not approve paper or live trading.

## Blocking Rules

The drill blocks import when an export has:

- missing required files
- missing benchmark, fees, slippage, positions, trades, equity curve, or strategy parameters
- unsupported run kind
- insufficient sample count
- sensitive data in metadata, logs, or CSV files

Sensitive-data patterns currently include:

- email
- China mobile phone number
- API key, token, secret, or access key
- account id or broker account
- order id or broker order

When any sensitive item is detected, normalization and import are blocked. The
report only stores a redacted excerpt for diagnosis.

## Output Contract

JSON output includes:

```text
workflow_id
scenario_id
batch_dir
normalize_dir
json_path
markdown_path
diagnosed_count
normalized_count
ready_count
blocked_count
field_issue_stats
diagnoses
batch_result
markdown
```

`field_issue_stats` includes:

```text
alias_mappings
missing_files
blockers
sensitive_patterns
```

`batch_result` is only present when every export is ready to import.

## Acceptance Criteria

A real JoinQuant batch is accepted when:

1. `blocked_count` is `0`.
2. `ready_count` equals `diagnosed_count`.
3. `batch_result.baseline_run_id` is present.
4. at least one candidate comparison exists.
5. `curve_payload.equity_curves` and `curve_payload.drawdown_curves` are non-empty.
6. the markdown report clearly states whether paper-trading discussion is allowed.
7. JSON and Markdown artifacts are saved to a private review path when requested.

Passing this drill means the evidence is reviewable. It is not live-trading
approval.
