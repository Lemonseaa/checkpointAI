# Workflow Evidence Next 20 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the next twenty evidence-harness steps around workflow import, validation, visualization, goal profiles, shadow queues, reports, and human decision memory.

**Architecture:** Keep all new backend behavior inside the Evidence Harness path. Do not add a generic workflow runtime, drag-and-drop builder, or platform layer. UI remains a read-only/control console over evidence, not a workflow editor.

**Tech Stack:** Python, Pydantic, SQLite, FastAPI, React, TypeScript, Tailwind, Playwright, unittest.

---

## Tasks

- [x] 1. Add Workflow Contract validation models and service.
- [x] 2. Add Workflow Map summary models for node roles, edges, coverage, black boxes, and metrics.
- [x] 3. Expose Workflow Map API endpoints.
- [x] 4. Add first read-only Workflow Graph UI improvements.
- [x] 5. Add Node Detail fields for inputs, outputs, metrics, latency, cost, and optimization eligibility.
- [x] 6. Add Evidence Gap Report and API.
- [x] 7. Add human-owned Optimization Goal Profile storage.
- [x] 8. Add Proposal explanation payload using evidence, target node, metric, risk, and next action.
- [x] 9. Add historical quant and content-style drill fixtures.
- [x] 10. Keep old modules bounded by evidence-path tests and docs.
- [x] 11. Add JSON/YAML workflow import format support where YAML is optional and JSON is required.
- [x] 12. Add minimal Adapter SDK contract for external workflow adapters.
- [x] 13. Add Trace Normalizer for inconsistent external traces.
- [x] 14. Add Metric Mapping API for business/system/data-quality/guardrail classification.
- [x] 15. Add Baseline Selection API support already present to UI workflows.
- [x] 16. Add Optimization Goal Profile API and UI surface.
- [x] 17. Add Candidate Generation Boundary model documenting allowed and blocked change types.
- [x] 18. Add Shadow Replay Queue storage/service skeleton for evidence proposals.
- [x] 19. Add Comparison Report export text for baseline-vs-candidate reviews.
- [x] 20. Add Human Decision Memory from approval/rejection history.

## Verification

- [x] `python -m unittest tests.evidence.test_workflow_contract_next20 -v`
- [x] `python -m unittest tests.support.test_v58_web_api.V58WebApiTest -v`
- [x] `python -m ruff check loop_harness tests scripts`
- [x] `python -m mypy loop_harness --show-error-codes --no-incremental`
- [x] `python scripts/ops/final_acceptance.py`
- [x] `npm run lint`
- [x] `npm run build`
- [x] `npm run e2e`
