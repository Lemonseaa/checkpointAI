# JoinQuant Real Drill Runner Plan

## Goal

Add a backend-only real-data drill runner for JoinQuant export batches.

The runner should automate the safe sequence:

```text
diagnose -> optional normalize -> validate -> batch import -> summary/report
```

## Steps

1. Add tests for sensitive-data blockers, drill summary, markdown output, CLI,
   and field issue statistics.
2. Add sensitive information scanning to JoinQuant diagnosis.
3. Add `JoinQuantRealDrillRunner` and summary models.
4. Add `loopharness evidence joinquant-real-drill`.
5. Add real-data acceptance documentation.
6. Run quant tests, full unittest, ruff, mypy, compile, and diff check.

## Boundaries

- No JoinQuant API integration.
- No automatic paper/live trading.
- No UI changes in this step.
- No hidden data downloads.
