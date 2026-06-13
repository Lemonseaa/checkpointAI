# Quant Data Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first A-share quant data loop with durable data contracts, vendor-grade source metadata, simple backtests, evidence conversion, and data quality gates.

**Architecture:** Add a focused `loop_harness.quant_data` package instead of expanding the existing evidence core. Providers normalize A-share market data into one durable contract; vendor CSV exports and Tushare-style API payloads are first-class sources; a minimal backtester produces baseline/candidate metrics; a pipeline converts those metrics into existing evidence payloads and review packages.

**Tech Stack:** Python standard library, Pydantic models already used by the project, optional runtime Tushare API bridge, existing `EvidenceHarness` and quant evidence contracts.

---

### Task 1: Market Data Contract

**Files:**
- Create: `loop_harness/quant_data/__init__.py`
- Create: `loop_harness/quant_data/models.py`
- Test: `tests/quant_data/test_market_data_models.py`

- [ ] Define `AShareMarketBar`, `AShareMarketDataSet`, `MarketDataQualityReport`, and `DataSourceKind`.
- [ ] Validate OHLCV rows: positive prices, high/low consistency, non-negative volume, chronological order.
- [ ] Compute quality flags: missing OHLCV, too few bars, duplicate trade dates, non-positive prices, missing adjustment mode, missing vendor/source metadata.

### Task 2: A-Share Data Providers

**Files:**
- Create: `loop_harness/quant_data/providers.py`
- Test: `tests/quant_data/test_market_data_providers.py`

- [ ] Add `MarketDataProvider` protocol.
- [ ] Add `AShareStaticProvider` only for deterministic tests and examples.
- [ ] Add `VendorCSVAShareProvider` for serious data exported from Tushare Pro, JoinQuant, RiceQuant, Choice, Wind, or a broker platform.
- [ ] Add `TushareDailyProvider` as an optional API bridge that requires an explicit token and never silently falls back to scraped data.
- [ ] Mark provider metadata with source, vendor, license note, adjusted mode, and whether the data is decision grade.

### Task 3: Minimal Backtester

**Files:**
- Create: `loop_harness/quant_data/backtest.py`
- Test: `tests/quant_data/test_backtester.py`

- [ ] Implement buy-and-hold baseline.
- [ ] Implement moving-average crossover candidate.
- [ ] Compute total_return, annual_return, sharpe, max_drawdown, win_rate, turnover, trade_count, sample_count.
- [ ] Keep formulas simple and deterministic; this is a harness validation backtester, not a production trading engine.

### Task 4: Evidence Pipeline

**Files:**
- Create: `loop_harness/quant_data/pipeline.py`
- Modify: `loop_harness/evidence/__init__.py`
- Test: `tests/quant_data/test_quant_data_pipeline.py`

- [ ] Convert backtest outputs to Workflow Contract v1 payloads.
- [ ] Ingest baseline and candidate through `EvidenceHarness`.
- [ ] Build comparison report and optimization chart.
- [ ] Preserve market data source, frequency, adjusted flag, and quality report in metadata.

### Task 5: CLI

**Files:**
- Modify: `loop_harness/evidence/cli.py`
- Test: `tests/quant_data/test_quant_data_cli.py`

- [ ] Add `loopharness evidence quant-loop-demo`.
- [ ] Add options for `--symbol`, `--provider static-a-share|vendor-csv|tushare`, `--data-path`, `--frequency`, `--start`, `--end`, `--adjusted`.
- [ ] Default to static A-share provider only for demo; production commands must prefer `vendor-csv` or `tushare`.
- [ ] Print baseline run id, candidate run id, recommendation, and quality status.

### Task 6: Docs and Verification

**Files:**
- Modify: `docs/business_lines/quant/README.md`
- Modify: `README.md`

- [ ] Document the A-share-first data source strategy.
- [ ] Document that AKShare-like scraped data is not the main path for serious evidence.
- [ ] Document that historical A-share data is research evidence, not live-trading proof.
- [ ] Run targeted quant-data tests, full unittest suite, ruff, mypy, and final acceptance when feasible.

---

## Self-Review

- Scope is intentionally limited to A-share historical data and simple backtests.
- No live trading, broker connection, or high-frequency data support is included.
- Tushare/network providers are optional and not required by tests.
- Evidence recommendations remain conservative because historical backtests are not live proof.
