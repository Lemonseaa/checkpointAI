# JoinQuant Validation And Strategy Config CLI Plan

## Goal

Make the A-share external backtest path safer before using real JoinQuant or
RQAlpha data:

1. Validate JoinQuant export directories before ingestion.
2. Prevent partial batch imports when one candidate is broken.
3. Convert structured StrategyProposal JSON into platform config drafts.
4. Document real-data sample expectations and current integration risks.

## Steps

1. Add tests for `joinquant-validate`, `joinquant-batch` preflight failure, and
   `strategy-proposal-to-config`.
2. Implement `joinquant-validate`.
3. Add JoinQuant batch preflight validation before any evidence is stored.
4. Implement StrategyProposal JSON loading and config conversion CLI.
5. Add real JoinQuant export sample README and integration risk review.
6. Run quant tests, full unittest, ruff, mypy, compile, and diff check.

## Boundaries

- Do not connect live JoinQuant APIs.
- Do not implement a backtest engine.
- Do not import TradingAgents directly.
- Do not claim paper/live readiness from fixtures.
