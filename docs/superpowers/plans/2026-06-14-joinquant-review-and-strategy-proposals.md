# JoinQuant Review And Strategy Proposals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make JoinQuant exports usable from CLI, generate review-ready packages and equity/drawdown chart payloads, and define the structured strategy proposal path needed before TradingAgents integration.

**Architecture:** Keep platform export parsing in `loop_harness.quant_data.platform_export`, add strategy proposal contracts in `loop_harness.quant_data.strategy_proposal`, and wire human-facing commands through the existing evidence CLI. TradingAgents remains planning-only in this iteration.

**Tech Stack:** Python standard library, Pydantic, existing `EvidenceHarness`, existing JoinQuant export adapter, existing evidence chart/report models.

---

### Task 1: JoinQuant Export CLI

- [ ] Add `loopharness evidence joinquant-import`.
- [ ] Add `loopharness evidence joinquant-batch`.
- [ ] Print run ids, comparison summaries, chart payload, and markdown.

### Task 2: JoinQuant Review Package

- [ ] Build review output from JoinQuant batch imports.
- [ ] Include comparison reports, chart payload, quality gate results, and paper-trading discussion text.

### Task 3: Equity And Drawdown Curve Payloads

- [ ] Parse `equity_curve.csv`.
- [ ] Generate equity curve and drawdown curve points.
- [ ] Attach curve payloads to JoinQuant batch result.

### Task 4: Strategy Proposal Contract

- [ ] Add `StrategyProposal`, `StrategyRiskConstraints`, and validation.
- [ ] Require hypothesis, strategy type, universe, parameters, expected metric, and reason.

### Task 5: Proposal To Backtest Config

- [ ] Convert moving-average, momentum, and mean-reversion proposals to platform config drafts.
- [ ] Keep output generic enough for JoinQuant and RQAlpha.

### Task 6: TradingAgents Integration Plan

- [ ] Document TradingAgents as research/proposal/interpretation layer.
- [ ] Explicitly forbid it from bypassing evidence gates, quality gates, or human final control.

---

## Self-Review

- No automatic JoinQuant login or browser automation.
- No live trading.
- No TradingAgents runtime integration yet.
- This step makes result import and proposal structure usable before connecting research agents.
