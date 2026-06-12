# R3 Evidence Review Package Next 20 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an evidence review package so every workflow change can be exported, replayed, inspected, and discussed by a human or Hermes without digging through SQLite or raw logs.

**Architecture:** Keep Loop Harness as the evidence/control layer, not the workflow runtime. A review package is a portable JSON/Markdown bundle containing workflow graph, chart payload, baseline comparison, gaps, run metadata, and recommended next action. The package is generated from stored evidence and can be replay-validated against the database.

**Tech Stack:** Python, Pydantic, SQLite, FastAPI, argparse CLI, React/TypeScript, unittest, Playwright.

---

## File Map

- Create `loop_harness/evidence/review_package.py`: package models, builder, markdown exporter.
- Create `loop_harness/evidence/replay.py`: package replay validator, drift detection.
- Modify `loop_harness/evidence/service.py`: add package and replay methods.
- Modify `loop_harness/harness.py`: expose package/replay facade.
- Modify `loop_harness/evidence/cli.py`: add package export/replay commands.
- Modify `loop_harness/api.py`: add package API endpoints.
- Modify `web/src/types/api.ts`: add review package types.
- Modify `web/src/api/client.ts`: add review package client methods.
- Create `web/src/features/evidence/EvidenceReviewPackage.tsx`: UI panel for package summary and export.
- Modify `web/src/features/evidence/EvidenceRunDetailPage.tsx`: show review package panel.
- Modify `web/tests/e2e/console.spec.ts`: verify package UI.
- Create `tests/evidence/test_evidence_review_package_next20.py`: Python package/replay tests.
- Modify `docs/core_innovation/impact_console.md`: document review package as the handoff artifact.
- Modify `docs/business_lines/quant/README.md`: document quant review package workflow.

---

## 20-Step Plan

### 1. Baseline Status And Guardrails

- [ ] Run `git status --short`.
- [ ] Expected: only this plan file is uncommitted before execution.
- [ ] Run generated-file scan:

```bash
find . -maxdepth 3 \( -name '.DS_Store' -o -name '__pycache__' -o -name 'test-results' -o -name 'playwright-report' \) -print
```

- [ ] Expected: no output.

### 2. Write Review Package Failing Test

- [ ] Create `tests/evidence/test_evidence_review_package_next20.py`.
- [ ] Add a test that seeds quant drill V2 data, calls `EvidenceHarness.review_package_for_runs(baseline, candidates)`, and asserts:
  - `package_id` is non-empty
  - `baseline_run_id` is present
  - `candidate_run_ids` has multiple candidates
  - `graph.summary` exists
  - `chart.guardrail_summary` exists
  - `comparison_reports` are included
  - `markdown` contains “Evidence Review Package”
- [ ] Run:

```bash
python -m unittest tests.evidence.test_evidence_review_package_next20 -v
```

- [ ] Expected: FAIL with `AttributeError: 'EvidenceHarness' object has no attribute 'review_package_for_runs'`.

### 3. Create Review Package Models

- [ ] Create `loop_harness/evidence/review_package.py`.
- [ ] Define:

```python
class EvidenceReviewPackage(BaseModel):
    package_id: str
    workflow_id: str
    scenario_id: str
    baseline_run_id: str
    candidate_run_ids: list[str]
    graph: WorkflowGraphPayload
    chart: OptimizationChartPayload
    comparison_reports: list[EvidenceReport]
    gap_summary: str
    recommended_action: str
    markdown: str
    metadata: dict[str, Any] = Field(default_factory=dict)
```

- [ ] Export model in `loop_harness/evidence/__init__.py`.
- [ ] Run target test.
- [ ] Expected: still FAIL until builder exists.

### 4. Implement EvidenceReviewPackageBuilder

- [ ] In `loop_harness/evidence/review_package.py`, add `EvidenceReviewPackageBuilder`.
- [ ] Constructor accepts no database dependency.
- [ ] `build(...)` accepts:
  - baseline run
  - candidate runs
  - graph payload
  - chart payload
  - comparison reports
  - gap reports
- [ ] Generate `package_id` as `review_{workflow_id}_{baseline}_{candidate_count}` with unsafe characters replaced by `_`.
- [ ] Recommended action:
  - `review_for_paper` if best candidate exists and no guardrail violation on best
  - `collect_more_evidence` if no best candidate
  - `reject_or_refine` if all candidates are weak or violated
- [ ] Run target test.
- [ ] Expected: still FAIL until service facade exists.

### 5. Add Markdown Export

- [ ] In `EvidenceReviewPackageBuilder`, add `_markdown(package)`.
- [ ] Markdown must include:
  - title
  - workflow/scenario
  - baseline
  - candidate list
  - best candidate
  - guardrail summary
  - comparison summaries
  - next action
- [ ] Add test assertion for “Guardrail Summary” and “Next Action”.
- [ ] Run target test.
- [ ] Expected: builder-level test passes once service is wired.

### 6. Add Service Package Method

- [ ] Modify `loop_harness/evidence/service.py`.
- [ ] Add:

```python
def review_package_for_runs(self, baseline_run_id: str, candidate_run_ids: list[str]) -> EvidenceReviewPackage:
```

- [ ] Use existing methods:
  - `optimization_chart_for_runs`
  - `graph_for_run` using best candidate if available, else first candidate
  - `compare` for each candidate
  - `gap_report` for candidate runs
- [ ] Raise `ValueError` for missing baseline/candidate.
- [ ] Run target test.
- [ ] Expected: service test passes if called directly.

### 7. Add Harness Facade Method

- [ ] Modify `loop_harness/harness.py`.
- [ ] Add:

```python
def review_package_for_runs(self, baseline_run_id: str, candidate_run_ids: list[str]) -> EvidenceReviewPackage:
    return self.service.review_package_for_runs(baseline_run_id, candidate_run_ids)
```

- [ ] Run target test.
- [ ] Expected: initial review package test passes.

### 8. Add Package JSON Export Test

- [ ] Extend `tests/evidence/test_evidence_review_package_next20.py`.
- [ ] Assert `package.model_dump(mode="json")` contains no Pydantic objects that cannot serialize.
- [ ] Assert `json.dumps(package.model_dump(mode="json"))` succeeds.
- [ ] Expected: package can be handed to Hermes or stored as a file.

### 9. Implement Replay Validator Model

- [ ] Create `loop_harness/evidence/replay.py`.
- [ ] Define:

```python
class ReplayValidationResult(BaseModel):
    package_id: str
    valid: bool
    missing_run_ids: list[str] = Field(default_factory=list)
    drifted_run_ids: list[str] = Field(default_factory=list)
    summary: str
```

- [ ] Export in `loop_harness/evidence/__init__.py`.
- [ ] Add failing test that imports `ReplayValidationResult`.
- [ ] Expected: import passes after model exists.

### 10. Implement PackageReplayValidator

- [ ] In `loop_harness/evidence/replay.py`, add `PackageReplayValidator`.
- [ ] Method:

```python
def validate(self, package: EvidenceReviewPackage, stored_runs: list[StoredEvidenceRun]) -> ReplayValidationResult:
```

- [ ] Check:
  - baseline run exists
  - every candidate exists
  - metric keys for package chart candidates still exist in stored runs
- [ ] Add test that deletes one candidate from the stored list and expects `valid=False`.
- [ ] Run target test.

### 11. Add Service Replay Method

- [ ] Modify `loop_harness/evidence/service.py`.
- [ ] Add:

```python
def validate_review_package(self, package: EvidenceReviewPackage) -> ReplayValidationResult:
```

- [ ] Load all package run ids from store.
- [ ] Delegate to `PackageReplayValidator`.
- [ ] Add harness facade method.
- [ ] Run target test.

### 12. Add CLI Export Command

- [ ] Modify `loop_harness/evidence/cli.py`.
- [ ] Add:

```bash
loopharness evidence package --baseline <run_id> --candidate <run_id> --candidate <run_id>
```

- [ ] Output JSON by default.
- [ ] Add `--markdown` flag to output Markdown only.
- [ ] Add CLI test using subprocess.
- [ ] Expected: CLI prints package JSON and Markdown.

### 13. Add CLI Replay Command

- [ ] Modify `loop_harness/evidence/cli.py`.
- [ ] Add:

```bash
loopharness evidence replay-package --path <package.json>
```

- [ ] Load package JSON from local path.
- [ ] Validate against current SQLite DB.
- [ ] Print `valid`, missing run ids, drifted run ids, summary.
- [ ] Add CLI test.

### 14. Add API Package Endpoints

- [ ] Modify `loop_harness/api.py`.
- [ ] Add:
  - `POST /api/evidence/review-packages`
  - `POST /api/evidence/review-packages/validate`
- [ ] Request body for create:

```json
{
  "baseline_run_id": "baseline",
  "candidate_run_ids": ["candidate"]
}
```

- [ ] Request body for validate is the package JSON.
- [ ] Extend `tests/support/test_v58_web_api.py`.
- [ ] Update fallback route manifest.

### 15. Add Frontend Types And Client

- [ ] Modify `web/src/types/api.ts`.
- [ ] Add `EvidenceReviewPackage` and `ReplayValidationResult`.
- [ ] Modify `web/src/api/client.ts`.
- [ ] Add:
  - `createReviewPackage(baselineRunId, candidateRunIds)`
  - `validateReviewPackage(packagePayload)`
- [ ] Run `npm run build`.
- [ ] Expected: TypeScript passes.

### 16. Build EvidenceReviewPackage UI

- [ ] Create `web/src/features/evidence/EvidenceReviewPackage.tsx`.
- [ ] Props:

```ts
type EvidenceReviewPackageProps = {
  packageData?: EvidenceReviewPackage;
  onCreate: () => void;
  isLoading: boolean;
};
```

- [ ] Show:
  - package id
  - baseline
  - candidates
  - recommended action
  - guardrail summary
  - Markdown preview
- [ ] No file download yet; show copyable text only.

### 17. Integrate Package UI Into Evidence Run Detail

- [ ] Modify `web/src/features/evidence/EvidenceRunDetailPage.tsx`.
- [ ] If baseline exists and current run is not baseline, show “Create review package”.
- [ ] On click, call `createReviewPackage`.
- [ ] Render `EvidenceReviewPackage`.
- [ ] Empty state if baseline is missing.

### 18. Extend E2E Coverage

- [ ] Modify `web/tests/e2e/console.spec.ts`.
- [ ] Mock `POST /api/evidence/review-packages`.
- [ ] Assert:
  - “Create review package” button exists
  - click shows package id
  - Markdown preview contains “Evidence Review Package”
  - recommended action appears
- [ ] Run `npm run e2e`.

### 19. Update Documentation

- [ ] Modify `docs/core_innovation/impact_console.md`.
- [ ] Add section “Review Package Handoff”.
- [ ] Explain:
  - package is the artifact for human/Hermes review
  - package is generated from evidence, not manually edited
  - package can be replay-validated
- [ ] Modify `docs/business_lines/quant/README.md`.
- [ ] Add CLI example:

```bash
loopharness evidence package --baseline csv_baseline --candidate csv_candidate_strong --candidate csv_candidate_weak
```

### 20. Full Verification And Risk Review

- [ ] Run:

```bash
python -m unittest discover -s tests -v
python -m ruff check loop_harness tests scripts
python -m mypy loop_harness --show-error-codes --no-incremental
npm run lint
npm run build
npm run e2e
python scripts/ops/final_acceptance.py
```

- [ ] Clean generated artifacts:

```bash
find . -name '__pycache__' -type d -prune -exec rm -rf {} +
find . -name '.DS_Store' -type f -delete
rm -rf web/test-results web/playwright-report
```

- [ ] Run `git diff --stat`.
- [ ] Confirm changes stay in evidence package/replay/API/UI/tests/docs.
- [ ] Report verification results.
- [ ] Do not commit or push unless the user asks.

---

## Exit Criteria

This block is complete when:

1. A baseline and candidates can be bundled into an evidence review package.
2. The package includes graph, chart, comparisons, gaps, recommendation, and Markdown.
3. The package can be replay-validated against SQLite.
4. CLI and API expose package generation.
5. Web UI shows package summary and Markdown preview.
6. Full Python + frontend + E2E + final acceptance checks pass.

## Explicit Non-Goals

- No automatic deployment from package.
- No automatic prompt rewrite.
- No external workflow execution.
- No file upload/download UI.
- No TradingAgents full adapter yet.
