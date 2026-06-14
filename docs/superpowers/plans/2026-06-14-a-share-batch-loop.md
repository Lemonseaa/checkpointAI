# A-Share Batch Quant Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the single-symbol A-share loop into a real-sample batch experiment path driven by manifest metadata, vendor CSV files, parameter grids, summary reports, and chart payloads.

**Architecture:** Keep this work inside `loop_harness.quant_data`. A manifest loader owns sample provenance, the batch runner orchestrates provider + backtester + evidence pipeline, and report models expose human-readable summaries without creating a new storage system.

**Tech Stack:** Python standard library, Pydantic, existing `EvidenceHarness`, existing `AShareQuantLoopPipeline`, existing evidence chart/report models.

---

### Task 1: A-Share Sample Manifest

- [ ] Add `AShareSampleManifestEntry` and `AShareSampleManifest`.
- [ ] Load `manifest.json` from `examples/a_share_data/`.
- [ ] Validate required fields: `ts_code`, `file_path`, `source_vendor`, `adjusted_mode`, `start_date`, `end_date`, `decision_grade`.

### Task 2: Data Quality Summary

- [ ] Add manifest-level quality summary: total samples, decision-grade count, non-decision-grade count, quality flags by symbol.
- [ ] Reuse `VendorCSVAShareProvider` and `AShareMarketDataSet.quality_report()`.

### Task 3: Batch Quant Loop Runner

- [ ] Add `AShareBatchQuantRunner`.
- [ ] Run the existing A-share pipeline across every manifest entry.
- [ ] Return baseline/candidate ids, recommendation, and quality status for every symbol.

### Task 4: Parameter Grid Search

- [ ] Add `AShareParameterGrid`.
- [ ] Generate only valid pairs where `fast_window < slow_window`.
- [ ] Run every valid pair for every manifest entry.

### Task 5: Batch Report

- [ ] Add JSON and Markdown report models.
- [ ] Answer which symbols were tested, which params ranked best, which candidates were rejected, and whether evidence is enough for paper-trading discussion.

### Task 6: Chart Payload Prep

- [ ] Add UI-ready payload: symbol ranking, parameter heatmap, quality distribution, recommendation distribution, and drawdown blockers.
- [ ] Document the `examples/a_share_data/` structure and CLI next steps.

---

## Self-Review

- Scope is A-share only.
- No live trading, broker integration, or non-A-share data.
- Static fixture data remains non-decision-grade.
- Vendor CSV is the serious path.
