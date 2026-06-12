# Examples

Examples are grouped by product responsibility.

## Evidence Mainline

```text
examples/evidence/
```

Contains external workflow run JSON examples used by the Evidence Harness.

```bash
loopharness evidence ingest examples/evidence/quant_baseline_run.json
loopharness evidence ingest examples/evidence/quant_candidate_run.json
loopharness evidence compare --baseline quant_baseline_001 --candidate quant_candidate_001
loopharness evidence ingest examples/evidence/content_baseline_run.json
loopharness evidence ingest examples/evidence/content_candidate_run.json
loopharness evidence compare --baseline content_baseline_001 --candidate content_candidate_001
```

## Support Examples

```text
examples/support/
```

Small examples for currently supported package entry points.

```bash
python examples/support/quickstart.py
```
