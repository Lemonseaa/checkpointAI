# TradingAgents Real Sample Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current TradingAgents-like export spike into a real-sample gate before any formal TradingAgents adapter is built.

**Architecture:** Keep TradingAgents as an external workflow candidate. Loop Harness should ingest exported evidence, validate whether it is observable enough, generate review packages, and produce a go/no-go compatibility report. Do not import TradingAgents Python internals and do not build an execution adapter until real samples prove the contract is stable.

**Tech Stack:** Python 3.11+, SQLite, unittest, ruff, mypy, React, TypeScript, Playwright.

---

### Task 1: Real Sample Intake Folder and Manifest

**Files:**
- Create: `docs/business_lines/quant/tradingagents_real_sample_gate.md`
- Create: `examples/tradingagents/README.md`
- Create: `examples/tradingagents/.gitkeep`
- Modify: `docs/business_lines/quant/tradingagents_adapter_plan.md`

- [ ] Create `examples/tradingagents/README.md` explaining that real exports are local operator-provided samples and should not contain secrets, broker credentials, private account identifiers, or live trading keys.
- [ ] Document the expected sample count: at least 5 historical exports before formal adapter work; 10+ preferred.
- [ ] Add a sample manifest format with fields: `sample_id`, `source_path`, `run_kind`, `market`, `time_range`, `contains_private_data`, `operator_notes`.
- [ ] Update the TradingAgents adapter plan to state that the current fixture is only a synthetic compatibility probe, not enough for adapter approval.

**Verification:**
- [ ] Run `python -m unittest tests.evidence.test_tradingagents_spike -v`.
- [ ] Run `git diff --check`.

### Task 2: Batch Conversion and Quality Summary

**Files:**
- Modify: `scripts/business_lines/quant/convert_tradingagents_export.py`
- Create: `tests/evidence/test_tradingagents_batch_conversion.py`

- [ ] Add CLI support for `--input-dir` and `--output-dir`.
- [ ] For each `*.json` export in `--input-dir`, convert it with `convert_tradingagents_export`.
- [ ] Write one converted contract payload per input file.
- [ ] Print a compact summary: converted count, failed count, missing required metrics, black-box trace warnings, average sample count.
- [ ] Add tests proving mixed success/failure batches return a non-zero exit code only when `--strict` is supplied.

**Verification:**
- [ ] Run `python -m unittest tests.evidence.test_tradingagents_spike tests.evidence.test_tradingagents_batch_conversion -v`.
- [ ] Run `python -m ruff check loop_harness tests scripts`.

### Task 3: TradingAgents Compatibility Score from Real Samples

**Files:**
- Create: `loop_harness/evidence/tradingagents_compatibility.py`
- Modify: `loop_harness/evidence/__init__.py`
- Create: `tests/evidence/test_tradingagents_compatibility.py`
- Modify: `docs/borrowed_wheels/adapter_checklist.md`

- [ ] Implement `score_tradingagents_samples(converted_payloads)` returning structured scores for input/output structure, prompt control, trace coverage, metric coverage, artifact quality, and integration effort.
- [ ] Treat missing trace, missing config surface, missing core quant metrics, and synthetic-only samples as blockers.
- [ ] Generate decision values: `go`, `needs_more_samples`, `needs_mapping_fix`, `no_go`.
- [ ] Update the adapter checklist to say the formal adapter decision is made from real sample compatibility score, not repository reputation.

**Verification:**
- [ ] Run `python -m unittest tests.evidence.test_tradingagents_compatibility -v`.
- [ ] Run `python -m mypy loop_harness --show-error-codes --no-incremental`.

### Task 4: Review Package Drill for TradingAgents Samples

**Files:**
- Create: `scripts/business_lines/quant/review_tradingagents_samples.py`
- Create: `tests/evidence/test_tradingagents_review_drill.py`
- Modify: `scripts/README.md`

- [ ] Add a script that converts a directory of TradingAgents exports, ingests successful payloads, and builds review packages.
- [ ] The script must output a human-readable summary: best candidate, weakest candidate, drawdown blockers, sample-size blockers, and whether paper trading discussion is justified.
- [ ] Keep the script read-only for source exports; do not modify original TradingAgents files.
- [ ] Document the script in `scripts/README.md`.

**Verification:**
- [ ] Run `python -m unittest tests.evidence.test_tradingagents_review_drill -v`.
- [ ] Run `python scripts/business_lines/quant/review_tradingagents_samples.py --help`.

### Task 5: UI Distinction Between Fixture, Synthetic, Historical, Paper, and Live

**Files:**
- Modify: `web/src/features/evidence/`
- Modify: `web/tests/e2e/console.spec.ts`
- Modify: `docs/RISK_REVIEW.md`

- [ ] Add visible run-kind badges for `fixture`, `synthetic`, `historical`, `paper`, and `live` evidence.
- [ ] Ensure TradingAgents-like fixture data is visually labeled as fixture/synthetic and cannot be mistaken for real historical evidence.
- [ ] Add E2E expectations that the TradingAgents-like workflow shows the run-kind badge and warning copy.
- [ ] Update risk review with the rule: no optimization claim may be made from fixture-only evidence.

**Verification:**
- [ ] Run `npm run lint` from `web/`.
- [ ] Run `npm run build` from `web/`.
- [ ] Run `npm run e2e` from `web/`.

### Task 6: Go/No-Go Report and Commit Gate

**Files:**
- Create: `docs/business_lines/quant/reports/tradingagents_spike_go_no_go.md`
- Modify: `docs/business_lines/quant/README.md`
- Modify: `docs/borrowed_wheels/adapter_checklist.md`

- [ ] Add a go/no-go report template with sections: sample inventory, compatibility score, evidence quality, missing fields, adapter effort, risk controls, decision.
- [ ] Link the report template from the quant business-line README.
- [ ] Add a final rule: a formal TradingAgents adapter can start only after the go/no-go report says `go` or `needs_mapping_fix` with explicit fixes.
- [ ] Commit only after the full verification suite passes or explicitly document any blocked browser/tooling check.

**Final Verification:**
- [ ] Run `python -m unittest discover -s tests -q`.
- [ ] Run `python -m ruff check loop_harness tests scripts`.
- [ ] Run `python -m mypy loop_harness --show-error-codes --no-incremental`.
- [ ] Run `python scripts/ops/final_acceptance.py`.
- [ ] Run `npm run lint`, `npm run build`, and `npm run e2e` from `web/`.
- [ ] Run `git diff --check`.
