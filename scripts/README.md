# Scripts

Scripts are grouped by responsibility.

```text
ops/                   Health checks, benchmark, stress, service entrypoint, final acceptance.
business_lines/quant/  Quant business-line historical drill scripts.
```

Use the ops scripts from the repository root:

```bash
python scripts/ops/health_check.py
python scripts/ops/final_acceptance.py
```

Run an evidence drill for the console:

```bash
python scripts/business_lines/run_evidence_drill.py --db data/loopharness.db --candidates 10
```

Convert a TradingAgents-like export into Loop Harness evidence JSON:

```bash
python scripts/business_lines/quant/convert_tradingagents_export.py \
  --input tests/fixtures/tradingagents_like_run.json \
  --output /tmp/tradingagents_evidence.json
```

Batch-convert a directory of sanitized TradingAgents exports:

```bash
python scripts/business_lines/quant/convert_tradingagents_export.py \
  --input-dir examples/tradingagents \
  --output-dir /tmp/tradingagents_evidence \
  --strict
```

Review converted TradingAgents samples through the evidence harness:

```bash
python scripts/business_lines/quant/review_tradingagents_samples.py \
  --input-dir examples/tradingagents \
  --db .runtime/tradingagents_review.db
```
