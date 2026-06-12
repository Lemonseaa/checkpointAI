# R3 Visual Evidence Next 20 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Loop Harness evidence into a visual, data-backed control surface that can show whether an external workflow became better after a change.

**Architecture:** Keep external workflow execution outside Loop Harness. Loop Harness ingests structured run evidence, builds graph/chart payloads, compares against baselines, and exposes human-readable UI/API/CLI reports. This plan prioritizes chartable optimization evidence and real quant data import before adding new autonomy.

**Tech Stack:** Python, Pydantic, SQLite, FastAPI, React, TypeScript, Tailwind, Playwright, unittest, ruff, mypy.

---

## File Map

- `loop_harness/evidence/charts.py`: UI-ready chart payload builders for run metrics, candidate comparison, and guardrail status.
- `loop_harness/evidence/csv_import.py`: CSV/backtest result importer that converts external quant results into Workflow Contract v1 payloads.
- `loop_harness/evidence/service.py`: Add chart and CSV ingest methods.
- `loop_harness/harness.py`: Expose chart and CSV ingest through the EvidenceHarness facade.
- `loop_harness/api.py`: Add chart and CSV ingest endpoints.
- `loop_harness/evidence/cli.py`: Add chart and CSV ingest commands.
- `web/src/types/api.ts`: Add chart payload types.
- `web/src/api/client.ts`: Add chart API client methods.
- `web/src/features/evidence/OptimizationCharts.tsx`: New visual chart panel for optimization impact.
- `web/src/features/evidence/EvidencePage.tsx`: Render optimization charts beside workflow graph.
- `web/src/features/evidence/EvidenceRunDetailPage.tsx`: Render per-run chart context.
- `docs/business_lines/quant/README.md`: Document real data import workflow.
- `docs/core_innovation/impact_console.md`: Document chart-first evidence rule.
- `tests/evidence/test_visual_evidence_next20.py`: Unit coverage for chart payloads and CSV import.
- `tests/support/test_v58_web_api.py`: API coverage for chart endpoints.
- `web/tests/e2e/console.spec.ts`: UI coverage for chart visibility.

---

## 20-Step Plan

### 1. Lock The Current Baseline

- [ ] Run `git status --short` and record the current uncommitted scope in the working notes.
- [ ] Do not commit yet unless the user explicitly asks.
- [ ] Confirm no generated files exist: `find . -maxdepth 3 \( -name '.DS_Store' -o -name '__pycache__' -o -name 'test-results' -o -name 'playwright-report' \) -print`.
- [ ] Expected: only source/docs/test changes remain.

### 2. Define The Visual Evidence Test Contract

- [ ] Create `tests/evidence/test_visual_evidence_next20.py`.
- [ ] Add a failing test for a chart payload built from a baseline and 3 candidates.
- [ ] Required assertions:
  - chart has `baseline_run_id`
  - chart has `candidate_points`
  - each point has `run_id`, `sharpe`, `max_drawdown`, `objective_score`, `guardrail_status`
  - weak/violating candidates are explicitly visible
- [ ] Run: `python -m unittest tests.evidence.test_visual_evidence_next20 -v`.
- [ ] Expected: FAIL because `loop_harness.evidence.charts` does not exist.

### 3. Implement Evidence Chart Models

- [ ] Create `loop_harness/evidence/charts.py`.
- [ ] Add Pydantic models:
  - `CandidateChartPoint`
  - `MetricTrendPoint`
  - `OptimizationChartPayload`
- [ ] Keep fields JSON/UI ready; do not introduce a charting library in Python.
- [ ] Run the visual evidence unit test.
- [ ] Expected: still FAIL until builder exists.

### 4. Implement OptimizationChartBuilder

- [ ] In `loop_harness/evidence/charts.py`, add `OptimizationChartBuilder`.
- [ ] Input: `StoredEvidenceRun` baseline, list of candidate `StoredEvidenceRun`, optional comparison reports.
- [ ] Output: `OptimizationChartPayload`.
- [ ] Classify guardrails:
  - `violated` if `max_drawdown > threshold`
  - `ok` otherwise
  - `unknown` when metric/schema is missing
- [ ] Run: `python -m unittest tests.evidence.test_visual_evidence_next20 -v`.
- [ ] Expected: PASS for the first chart model test.

### 5. Add Service And Harness Chart Methods

- [ ] Modify `loop_harness/evidence/service.py`.
- [ ] Add:
  - `optimization_chart(workflow_id: str) -> OptimizationChartPayload`
  - `optimization_chart_for_runs(baseline_run_id: str, candidate_run_ids: list[str]) -> OptimizationChartPayload`
- [ ] Modify `loop_harness/harness.py` to expose the same facade methods.
- [ ] Add tests that call through `EvidenceHarness`, not only `EvidenceService`.
- [ ] Expected: facade stays the main human/API entry point.

### 6. Add Chart API Endpoints

- [ ] Modify `loop_harness/api.py`.
- [ ] Add:
  - `GET /api/evidence/workflows/{workflow_id}/charts/optimization`
  - `POST /api/evidence/charts/optimization`
- [ ] Update fallback route manifest.
- [ ] Extend `tests/support/test_v58_web_api.py`.
- [ ] Run targeted API tests.
- [ ] Expected: API returns chart payload and 404/error envelope for missing runs.

### 7. Add Chart CLI Commands

- [ ] Modify `loop_harness/evidence/cli.py`.
- [ ] Add:
  - `loopharness evidence chart --workflow <workflow_id>`
  - `loopharness evidence chart --baseline <run_id> --candidate <run_id> [--candidate <run_id>]`
- [ ] Output readable JSON.
- [ ] Add CLI assertions to `tests/evidence/test_visual_evidence_next20.py`.
- [ ] Expected: user can inspect chart data without opening the Web UI.

### 8. Add CSV Import Test Fixture

- [ ] Create a small test CSV fixture under `tests/fixtures/quant_backtest_results.csv`.
- [ ] Required columns:
  - `run_id`
  - `fast_window`
  - `slow_window`
  - `total_return`
  - `sharpe`
  - `max_drawdown`
  - `win_rate`
  - `turnover`
  - `trade_count`
- [ ] Add one strong candidate and one weak guardrail-violating candidate.
- [ ] Expected: fixture validates real import shape, not only synthetic drill generation.

### 9. Implement Quant CSV Importer

- [ ] Create `loop_harness/evidence/csv_import.py`.
- [ ] Add `QuantBacktestCSVImporter`.
- [ ] Input: CSV path, workflow_id, scenario_id, run_kind.
- [ ] Output: list of Workflow Contract v1 payload dictionaries.
- [ ] Validate required columns and numeric parsing.
- [ ] Mark imported runs with metadata:
  - `data_source: csv_import`
  - `importer: QuantBacktestCSVImporter`
- [ ] Run importer unit tests.
- [ ] Expected: invalid CSV fails clearly; valid CSV produces ingestable payloads.

### 10. Wire CSV Import Into Evidence Harness

- [ ] Modify `loop_harness/evidence/service.py` and `loop_harness/harness.py`.
- [ ] Add `ingest_quant_csv(path, workflow_id, scenario_id, run_kind)`.
- [ ] Ingest every generated payload into SQLite.
- [ ] Return count and run ids.
- [ ] Add tests that import the CSV fixture and then build a chart from imported runs.
- [ ] Expected: imported data can be graphed and compared immediately.

### 11. Add CSV Import CLI

- [ ] Modify `loop_harness/evidence/cli.py`.
- [ ] Add:
  - `loopharness evidence import-quant-csv --path <csv> --workflow <id> --scenario quant --kind historical`
- [ ] Print imported run ids and a short warning that this is not live trading evidence.
- [ ] Add CLI test.
- [ ] Expected: one command gets real-ish backtest output into Loop Harness.

### 12. Add CSV Import API

- [ ] Modify `loop_harness/api.py`.
- [ ] Add `POST /api/evidence/import/quant-csv`.
- [ ] Keep request body simple:
  - `path`
  - `workflow_id`
  - `scenario_id`
  - `run_kind`
- [ ] This is local-first; do not implement file upload yet.
- [ ] Add API test.
- [ ] Expected: API can import a local CSV path when running on the same machine.

### 13. Add Frontend Chart Types And Client

- [ ] Modify `web/src/types/api.ts`.
- [ ] Add `OptimizationChartPayload`, `CandidateChartPoint`, `MetricTrendPoint`.
- [ ] Modify `web/src/api/client.ts`.
- [ ] Add `getOptimizationChart(workflowId)` and `buildOptimizationChart(payload)`.
- [ ] Run `npm run build`.
- [ ] Expected: TypeScript compiles with no `any` leak for chart payloads.

### 14. Build OptimizationCharts UI Component

- [ ] Create `web/src/features/evidence/OptimizationCharts.tsx`.
- [ ] Use simple SVG/HTML charting first, not a heavy chart library.
- [ ] Show:
  - Sharpe vs max drawdown scatter
  - candidate quality badges
  - guardrail violation list
  - best candidate marker
- [ ] Keep the visual deterministic for E2E.
- [ ] Expected: users can see optimization effect without reading JSON.

### 15. Integrate Charts Into Evidence Page

- [ ] Modify `web/src/features/evidence/EvidencePage.tsx`.
- [ ] Fetch optimization chart for selected workflow.
- [ ] Render `OptimizationCharts` below Workflow Visualization.
- [ ] Empty state: “Need at least one baseline and one candidate.”
- [ ] Expected: Evidence page becomes graph + chart control surface.

### 16. Integrate Charts Into Run Detail Page

- [ ] Modify `web/src/features/evidence/EvidenceRunDetailPage.tsx`.
- [ ] Show whether the current run appears in the optimization chart.
- [ ] If the run violates a guardrail, show it near the report summary.
- [ ] Expected: per-run detail makes risk visible immediately.

### 17. Extend E2E With Chart Assertions

- [ ] Modify `web/tests/e2e/console.spec.ts`.
- [ ] Mock chart endpoint.
- [ ] Assert:
  - chart panel appears
  - strong candidate appears
  - weak/guardrail candidate appears
  - “max_drawdown violated” or equivalent warning appears
- [ ] Run: `npm run e2e`.
- [ ] Expected: browser test proves the UI communicates optimization impact visually.

### 18. Update Product Docs

- [ ] Modify `docs/core_innovation/impact_console.md`.
- [ ] Add “visual proof before optimization” rule:
  - every proposed improvement should have a chartable before/after view when metrics exist.
- [ ] Modify `docs/business_lines/quant/README.md`.
- [ ] Document:
  - quant CSV import
  - chart generation
  - historical vs paper vs live evidence boundary
- [ ] Expected: docs match the new product direction.

### 19. Run Full Verification

- [ ] Run:
  - `python -m unittest discover -s tests -v`
  - `python -m ruff check loop_harness tests scripts`
  - `python -m mypy loop_harness --show-error-codes --no-incremental`
  - `npm run lint`
  - `npm run build`
  - `npm run e2e`
  - `python scripts/ops/final_acceptance.py`
- [ ] Clean generated artifacts after acceptance:
  - `find . -name '__pycache__' -type d -prune -exec rm -rf {} +`
  - `find . -name '.DS_Store' -type f -delete`
  - `rm -rf web/test-results web/playwright-report`
- [ ] Expected: all checks pass and no generated files remain.

### 20. Review The Work Against Product Direction

- [ ] Run `git diff --stat`.
- [ ] Check that changes stay inside Evidence Harness, quant business line, API, UI, tests, and docs.
- [ ] Confirm no new framework-runtime/platform wheel was introduced.
- [ ] Confirm the result answers:
  - What changed?
  - Did it get better?
  - Where is the risk?
  - Can the human see it visually?
- [ ] Report the result to the user with verification output.
- [ ] Do not commit/push unless the user asks.

---

## Exit Criteria

This 20-step block is complete when:

1. A quant CSV/backtest output can be imported.
2. Imported runs become evidence runs.
3. Baseline/candidate impact can be charted.
4. Weak and guardrail-violating candidates are visible, not hidden.
5. Web UI shows both workflow graph and optimization charts.
6. Full Python + frontend + E2E + final acceptance checks pass.

## Explicit Non-Goals

- No live trading.
- No automatic deployment.
- No TradingAgents full adapter yet.
- No drag-and-drop workflow builder.
- No new heavy charting dependency unless the simple chart proves insufficient.
