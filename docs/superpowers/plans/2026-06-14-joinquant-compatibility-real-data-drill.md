# JoinQuant Compatibility And Real Data Drill Plan

## Goal

Prepare the A-share JoinQuant path for real exported backtest data.

## Steps

1. Add field alias support for common JoinQuant export column names.
2. Add `joinquant-diagnose` to explain missing files, alias mappings, blockers,
   and import readiness.
3. Add `joinquant-normalize` to write a standard Quant Platform Export Contract
   copy when aliases are repairable.
4. Add `import_readiness_summary` to batch import results.
5. Add batch StrategyProposal JSON to platform config conversion.
6. Document the first real JoinQuant data drill.

## Boundaries

- No JoinQuant API calls.
- No broker or paper-trading execution.
- No hidden data downloads.
- No automatic approval from historical data.
