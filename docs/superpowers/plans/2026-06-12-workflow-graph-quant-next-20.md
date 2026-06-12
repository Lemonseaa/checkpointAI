# Workflow Graph + Quant Drill Next 20 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Productize the workflow graph surface and make the quant drill more realistic without building a workflow engine.

**Architecture:** Add graph payloads, graph API, UI graph improvements, metric source mapping, proposal targeting, and quant drill v2 fixtures/services inside the Evidence Harness path. Keep all live trading and publishing blocked.

**Tech Stack:** Python, Pydantic, SQLite, FastAPI, React, TypeScript, Tailwind, Playwright, unittest.

---

## Tasks

- [ ] 1. Define `WorkflowGraphPayload` and graph node/edge DTOs.
- [ ] 2. Add `GET /api/evidence/workflows/{workflow_id}/graph` and `GET /api/evidence/runs/{run_id}/graph`.
- [ ] 3. Standardize workflow node types.
- [ ] 4. Add deterministic graph layout fields.
- [ ] 5. Replace simple arrow-only workflow view with graph-card layout.
- [ ] 6. Add graph legend and client-side filters.
- [ ] 7. Strengthen node detail panel with artifacts/gaps/metric sources.
- [ ] 8. Mark evidence gaps directly in graph node payloads.
- [ ] 9. Add metric source mapping from trace events to graph nodes.
- [ ] 10. Add proposal targeting metadata for target node/config surface/expected metric.
- [ ] 11. Define quant adapter input contract.
- [ ] 12. Define quant backtest output contract.
- [ ] 13. Add expanded quant historical fixtures, including weak and failing candidates.
- [ ] 14. Add Quant Drill Runner v2 candidate generation.
- [ ] 15. Add quant report chart-ready payload.
- [ ] 16. Strengthen guardrail review summary.
- [ ] 17. Expose shadow queue data in UI.
- [ ] 18. Expand decision memory UI.
- [ ] 19. Document next legacy cleanup targets.
- [ ] 20. Add an end-to-end drill command/report for graph + quant evidence.

## Verification

- [ ] `python -m unittest tests.evidence.test_workflow_graph_quant_next20 -v`
- [ ] `python -m unittest tests.support.test_v58_web_api.V58WebApiTest -v`
- [ ] `python -m ruff check loop_harness tests scripts`
- [ ] `python -m mypy loop_harness --show-error-codes --no-incremental`
- [ ] `python scripts/ops/final_acceptance.py`
- [ ] `npm run lint`
- [ ] `npm run build`
- [ ] `npm run e2e`
