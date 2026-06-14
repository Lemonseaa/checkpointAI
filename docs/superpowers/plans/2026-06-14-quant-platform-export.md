# Quant Platform Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect real quant platform backtest exports, starting with JoinQuant-style export directories, without cloning platform backtest engines.

**Architecture:** Add a focused export adapter layer under `loop_harness.quant_data`. The platform export contract normalizes directory files, the JoinQuant adapter parses one export into Workflow Contract v1, quality gates reject weak exports, and a batch importer compares baseline/candidates through existing `EvidenceHarness`.

**Tech Stack:** Python standard library, Pydantic, existing `EvidenceHarness`, existing evidence comparison/chart/report models.

---

### Task 1: Quant Platform Export Contract

- [ ] Add `QuantPlatformExport`, `QuantPlatformMetadata`, and validation for `metadata.json`, `metrics.json`, `equity_curve.csv`, `trades.csv`, `positions.csv`, and optional `logs.txt`.
- [ ] Preserve platform, strategy, benchmark, cash, commission, slippage, frequency, run kind, and strategy parameters.

### Task 2: JoinQuant Export Adapter

- [ ] Add `JoinQuantExportAdapter`.
- [ ] Parse a JoinQuant-style export directory.
- [ ] Convert it into one Evidence payload with nodes, trace, metrics, config, artifacts, and metadata.

### Task 3: JoinQuant Export Quality Gate

- [ ] Add quality report with blockers for missing benchmark, missing fee/slippage, missing equity/trades/positions, short sample, abnormal equity jumps, missing strategy parameters, and unsupported run kind.
- [ ] Ensure blocked exports cannot be recommended for paper-trading discussion.

### Task 4: Batch JoinQuant Export Import

- [ ] Import one directory containing `baseline/` and candidate subdirectories.
- [ ] Ingest all exports, compare candidates against baseline, build chart payload, and generate Markdown.

### Task 5: RQAlpha Local Runner Plan

- [ ] Add a planning document for RQAlpha local execution and export conversion.
- [ ] Do not implement RQAlpha execution yet.

### Task 6: Quant Platform Docs

- [ ] Update quant docs with platform roles: data source, backtest execution, TradingAgents research, Loop Harness evidence control.
- [ ] Include the JoinQuant export folder shape and commands.

---

## Self-Review

- This plan does not automate JoinQuant login or browser operations.
- This plan does not implement live trading or simulated trading.
- JoinQuant exports are evidence inputs; Loop Harness remains evidence/control layer.
