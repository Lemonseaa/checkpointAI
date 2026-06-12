# Loop Harness Next 10 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tighten Loop Harness around its evidence-harness positioning by improving docs, workflow contracts, demo data, visualization, approvals, and adapter readiness.

**Architecture:** Keep Loop Harness narrow: external workflows enter through evidence contracts, become workflow maps and reports, and surface human decisions through the console. Do not add a workflow builder, agent runtime replacement, or plugin marketplace.

**Tech Stack:** Python 3.11+, SQLite, FastAPI, React, TypeScript, Tailwind, Playwright, unittest, ruff, mypy.

---

### Task 1: Post-Rename Stability Check

**Files:**
- Modify: `docs/superpowers/plans/2026-06-12-loop-harness-next-10.md`

- [ ] Run old-name scan for legacy brand and package tokens from before the Loop Harness rename.
- [ ] Run `python -m ruff check loop_harness tests scripts`.
- [ ] Run `python -m mypy loop_harness --show-error-codes --no-incremental`.
- [ ] Run `python -m unittest discover -s tests -q`.
- [ ] Run `npm run lint`, `npm run build`, and `npm run e2e` from `web/`.

### Task 2: Product README

**Files:**
- Modify: `README.md`

- [ ] Rewrite the top section around Loop Harness as an evidence-driven workflow control layer.
- [ ] Keep quick start commands accurate for `loopharness`.
- [ ] Add a compact “when to use / when not to use” section.

### Task 3: Core Architecture Diagram

**Files:**
- Modify: `README.md`
- Modify: `docs/BLUEPRINT.md`

- [ ] Add a Mermaid diagram for external workflow ingestion, visualization, comparison, proposal, approval, and rollback.
- [ ] Keep the diagram diagnostic, not workflow-builder oriented.

### Task 4: Workflow Contract v1

**Files:**
- Create: `docs/core_innovation/workflow_contract_v1.md`
- Modify: `docs/core_innovation/README.md`

- [ ] Define required fields: workflow, run, trace, metrics, config surface, artifacts.
- [ ] Define minimum viable adapter output and rejection conditions.
- [ ] Link the contract from the core innovation index.

### Task 5: Built-In Demo Workflow

**Files:**
- Create or modify: `examples/evidence/`
- Modify: `docs/business_lines/demo/README.md`

- [ ] Ensure demo evidence is independent from `opc_agent`.
- [ ] Include baseline and candidate JSON with nodes, edges, trace, metrics, and config surface.
- [ ] Document the demo’s business value and limitations.

### Task 6: Evidence Console Charts

**Files:**
- Modify: `web/src/features/evidence/`
- Modify: `web/tests/e2e/console.spec.ts`

- [ ] Add clear baseline-vs-candidate metric visualization.
- [ ] Add cumulative or trend-oriented effect summary when data is available.
- [ ] Cover the visual output in E2E.

### Task 7: Approval Decision Console

**Files:**
- Modify: `web/src/features/`
- Modify: `loop_harness/api.py`

- [ ] Make approval detail show change, reason, evidence, shadow result, risk, and suggested operation.
- [ ] Keep actions limited to approve, reject, and comment.

### Task 8: Workflow Visualization Page

**Files:**
- Modify: `web/src/features/evidence/`
- Modify: `README.md`

- [ ] Add a first-class workflow visualization page or route.
- [ ] Show nodes, edges, black boxes, trace coverage, metric coverage, cost, latency, and errors.

### Task 9: Adapter Compatibility Checklist v1

**Files:**
- Modify: `docs/borrowed_wheels/adapter_checklist.md`
- Modify: `docs/borrowed_wheels/reference_projects.md`

- [ ] Make the checklist concrete enough to score TradingAgents, Dify workflows, CrewAI, and custom scripts.
- [ ] Add go/no-go guidance before writing adapter code.

### Task 10: First Real External Workflow Plan

**Files:**
- Create: `docs/business_lines/quant/tradingagents_adapter_plan.md`
- Modify: `docs/business_lines/quant/README.md`

- [ ] Plan TradingAgents as the first serious external workflow candidate.
- [ ] Define what Loop Harness should observe, not replace.
- [ ] Define minimum data needed before optimization claims.

### Final Verification

- [ ] Run `python -m ruff check loop_harness tests scripts`.
- [ ] Run `python -m mypy loop_harness --show-error-codes --no-incremental`.
- [ ] Run `python -m unittest discover -s tests -q`.
- [ ] Run `python scripts/ops/final_acceptance.py`.
- [ ] Run `npm run lint`, `npm run build`, and `npm run e2e`.
