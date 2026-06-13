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
