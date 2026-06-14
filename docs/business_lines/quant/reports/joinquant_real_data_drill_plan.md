# JoinQuant Real Data Drill Plan

## Goal

Run the first real A-share JoinQuant export drill without pretending it proves a
tradable strategy.

The drill validates whether Loop Harness can ingest, diagnose, normalize,
compare, and visualize real exported backtest evidence.

## Minimum Dataset

Use at least:

```text
1 baseline export
5 candidate exports
same universe
same benchmark
same adjustment mode
same commission and slippage assumptions
historical run_kind
sample_count >= 120 per export
```

## Required Local Shape

```text
/private/path/joinquant_exports/
├── baseline/
├── candidate_001/
├── candidate_002/
├── candidate_003/
├── candidate_004/
└── candidate_005/
```

Do not commit this private directory.

## Drill Sequence

1. Diagnose one export:

```bash
loopharness evidence joinquant-diagnose \
  --export-dir /private/path/joinquant_exports/baseline
```

2. Normalize if the diagnosis shows field aliases:

```bash
loopharness evidence joinquant-normalize \
  --export-dir /private/path/joinquant_exports/baseline \
  --output-dir /private/path/joinquant_normalized/baseline
```

3. Validate every normalized export:

```bash
loopharness evidence joinquant-validate \
  --export-dir /private/path/joinquant_normalized/candidate_001
```

4. Batch import only after validation:

```bash
loopharness evidence joinquant-batch \
  --batch-dir /private/path/joinquant_normalized \
  --workflow joinquant_real_drill_001 \
  --scenario quant_a_share
```

5. Review:

```bash
loopharness evidence chart \
  --workflow joinquant_real_drill_001
```

## Pass Criteria

The drill passes only if:

1. Every export has a diagnosis report.
2. Every alias mapping is explicit.
3. No batch partially imports.
4. Equity and drawdown curves render.
5. `import_readiness_summary.ready_count >= 6`.
6. At least one comparison report explains why a candidate is better, worse, or inconclusive.
7. The report still says historical evidence is not live-trading approval.

## Failure Criteria

Stop and repair the input data if:

```text
missing benchmark
missing fees or slippage
mixed adjustment modes
mixed benchmark assumptions
sample_count below threshold
empty trades or positions
unexplained abnormal equity jumps
```

## Output Expected

The drill should produce:

```text
diagnosis JSON
normalized export directories
batch import JSON
equity curve payload
drawdown curve payload
comparison reports
paper-trading discussion note
```

## Decision Boundary

This drill can support:

```text
data contract validation
historical comparison review
paper-trading discussion
```

It cannot support:

```text
automatic simulated trading
automatic live trading
capital deployment
profit claims
```
