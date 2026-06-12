# R4 Review Package Decision Flow Next 20 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn evidence review packages from passive handoff artifacts into first-class human decision records that enter Approval Inbox, can be approved/rejected with comments, and feed decision memory without mutating external workflows.

**Architecture:** Keep Loop Harness as the evidence/control layer. Review packages remain immutable evidence bundles; decisions are separate records linked to package id, baseline id, candidate ids, scenario id, and workflow id. Approval does not deploy, trade, publish, or edit prompts; it only records a human decision and updates learning/decision memory.

**Tech Stack:** Python, Pydantic, SQLite, FastAPI, argparse CLI, React/TypeScript, unittest, Playwright.

---

## File Map

- Modify `loop_harness/evidence/review_package.py`: add decision-facing fields only if needed, without making package mutable.
- Create `loop_harness/evidence/review_decision.py`: decision model and decision store.
- Modify `loop_harness/evidence/service.py`: add submit/approve/reject/list package decision methods.
- Modify `loop_harness/harness.py`: expose review decision facade methods.
- Modify `loop_harness/evidence/cli.py`: add `package submit`, `package decision`, and `package decisions`.
- Modify `loop_harness/api.py`: add review package decision endpoints.
- Modify `loop_harness/console/approval_inbox.py` or equivalent inbox module: surface pending review package decisions.
- Modify `web/src/types/api.ts`: add review package decision types.
- Modify `web/src/api/client.ts`: add review decision client methods.
- Modify `web/src/features/evidence/EvidenceReviewPackage.tsx`: add “Submit for approval” action and decision state.
- Modify `web/src/features/approvals/*`: render review package approval details if existing approval UI needs type branching.
- Create `tests/evidence/test_review_package_decision_flow_next20.py`: backend/CLI/API decision-flow tests.
- Modify `tests/support/test_v58_web_api.py`: API contract coverage.
- Modify `web/tests/e2e/console.spec.ts`: UI approval flow coverage.
- Modify `docs/core_innovation/impact_console.md`: document review package decision flow.
- Modify `docs/core_innovation/user_preference.md`: document human-owned approval comments as preference evidence.

---

## 20-Step Plan

### 1. Baseline Status And Guardrails

- [ ] Run `git status --short`.
- [ ] Expected: current R3 review package changes may still be uncommitted; do not overwrite or revert them.
- [ ] Run:

```bash
find loop_harness tests scripts -name '__pycache__' -type d -print
```

- [ ] Expected: no output before starting. If output appears, remove generated cache only.

### 2. Write Failing Decision Flow Test

- [ ] Create `tests/evidence/test_review_package_decision_flow_next20.py`.
- [ ] Test name: `test_review_package_can_be_submitted_approved_and_recorded`.
- [ ] Seed V2 quant drill data, build a review package, call the desired API:

```python
decision = harness.submit_review_package(package, reason="Candidate is ready for human review.")
```

- [ ] Assert:
  - decision has `package_id`
  - status is `pending`
  - scenario/workflow/baseline/candidates are copied from package
  - `approval_required` is true
- [ ] Run:

```bash
python -m unittest tests.evidence.test_review_package_decision_flow_next20 -v
```

- [ ] Expected: FAIL with `AttributeError: 'EvidenceHarness' object has no attribute 'submit_review_package'`.

### 3. Define Review Decision Model

- [ ] Create `loop_harness/evidence/review_decision.py`.
- [ ] Add:

```python
class ReviewDecisionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewPackageDecision(BaseModel):
    decision_id: str
    package_id: str
    scenario_id: str
    workflow_id: str
    baseline_run_id: str
    candidate_run_ids: list[str]
    recommended_action: str
    status: ReviewDecisionStatus
    reason: str
    comment: str | None = None
    created_at: datetime
    decided_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

- [ ] Export it from `loop_harness/evidence/__init__.py`.
- [ ] Run the target test.
- [ ] Expected: still FAIL until harness/service methods exist.

### 4. Implement SQLite Decision Store

- [ ] In `loop_harness/evidence/review_decision.py`, add `ReviewPackageDecisionStore`.
- [ ] Table: `evidence_review_decisions`.
- [ ] Columns: `decision_id`, `package_id`, `scenario_id`, `workflow_id`, `baseline_run_id`, `candidate_run_ids_json`, `recommended_action`, `status`, `reason`, `comment`, `created_at`, `decided_at`, `metadata_json`.
- [ ] Indexes: `package_id`, `scenario_id`, `status`, `created_at`.
- [ ] Methods:

```python
create(decision: ReviewPackageDecision) -> ReviewPackageDecision
get(decision_id: str) -> ReviewPackageDecision | None
list(scenario_id: str | None = None, status: ReviewDecisionStatus | None = None) -> list[ReviewPackageDecision]
update_status(decision_id: str, status: ReviewDecisionStatus, comment: str) -> ReviewPackageDecision
```

- [ ] Add test `test_review_decision_store_persists_and_filters`.
- [ ] Run target test.

### 5. Add Service Submit Method

- [ ] Modify `loop_harness/evidence/service.py`.
- [ ] Add:

```python
def submit_review_package(self, package: EvidenceReviewPackage, reason: str) -> ReviewPackageDecision:
```

- [ ] Validation:
  - reject empty reason with `ValueError("Review package submission requires a reason.")`
  - call `validate_review_package(package)`
  - reject invalid replay with `ValueError("Review package is not replay-valid: ...")`
- [ ] Store pending decision through `ReviewPackageDecisionStore(self.store.path)`.
- [ ] Run target test.

### 6. Add Approve/Reject Service Methods

- [ ] Modify `loop_harness/evidence/service.py`.
- [ ] Add:

```python
def approve_review_package(self, decision_id: str, comment: str) -> ReviewPackageDecision:
def reject_review_package(self, decision_id: str, comment: str) -> ReviewPackageDecision:
```

- [ ] Validation:
  - reject empty comment
  - reject missing decision id
  - reject already decided decisions
- [ ] Add test that approves once and second approval raises `ValueError`.
- [ ] Run target test.

### 7. Expose Harness Facade

- [ ] Modify `loop_harness/harness.py`.
- [ ] Add:

```python
def submit_review_package(self, package: EvidenceReviewPackage, reason: str) -> ReviewPackageDecision:
def approve_review_package(self, decision_id: str, comment: str) -> ReviewPackageDecision:
def reject_review_package(self, decision_id: str, comment: str) -> ReviewPackageDecision:
def list_review_package_decisions(self, scenario_id: str | None = None, status: str | None = None) -> list[ReviewPackageDecision]:
```

- [ ] Keep all methods delegating to `EvidenceService`.
- [ ] Run target test.
- [ ] Expected: first decision flow test passes.

### 8. Record Decision Log On Approval/Rejection

- [ ] Decide whether to write to existing `DecisionLogStore` from the API layer or service layer.
- [ ] Preferred: API layer records operator-facing decision log; service layer stays evidence-only.
- [ ] Add backend test in `tests/support/test_v58_web_api.py` that approval endpoint creates a decision record if existing decision log API exposes it.
- [ ] If decision log cannot be queried cleanly, assert the evidence decision store status instead and document the limitation.

### 9. Add CLI Submit Command

- [ ] Modify `loop_harness/evidence/cli.py`.
- [ ] Add subcommand:

```bash
loopharness evidence package-submit --path package.json --reason "Candidate ready for review"
```

- [ ] Output JSON decision.
- [ ] Add CLI test using subprocess:
  - create package JSON
  - submit package
  - assert output status is `pending`
- [ ] Run target test.

### 10. Add CLI Decision Commands

- [ ] Modify `loop_harness/evidence/cli.py`.
- [ ] Add:

```bash
loopharness evidence package-decide --id <decision_id> --approve --comment "Approved for paper review"
loopharness evidence package-decide --id <decision_id> --reject --comment "Evidence is too weak"
loopharness evidence package-decisions --scenario quant --status pending
```

- [ ] Validation:
  - exactly one of `--approve` or `--reject`
  - comment required
- [ ] Add CLI tests for approve and reject paths.
- [ ] Run target test.

### 11. Add API Submit Endpoint

- [ ] Modify `loop_harness/api.py`.
- [ ] Add:

```text
POST /api/evidence/review-packages/submit
```

- [ ] Request:

```json
{
  "package": { "...": "EvidenceReviewPackage JSON" },
  "reason": "Candidate ready for review"
}
```

- [ ] Return `ReviewPackageDecision`.
- [ ] Errors:
  - 400 for missing reason/package
  - 400 for invalid replay package
- [ ] Extend `tests/support/test_v58_web_api.py`.

### 12. Add API List/Approve/Reject Endpoints

- [ ] Modify `loop_harness/api.py`.
- [ ] Add:

```text
GET  /api/evidence/review-decisions?scenario_id=quant&status=pending
POST /api/evidence/review-decisions/{decision_id}/approve
POST /api/evidence/review-decisions/{decision_id}/reject
```

- [ ] Request body for approve/reject:

```json
{"comment": "Human decision comment"}
```

- [ ] Return updated decision.
- [ ] Add fallback route manifest entries.
- [ ] Extend API tests.

### 13. Bridge Pending Review Decisions Into Approval Inbox

- [ ] Inspect existing approval inbox implementation.
- [ ] Add review package decisions as item type `evidence_review_package`.
- [ ] The inbox item detail should include:
  - package id
  - baseline id
  - candidate ids
  - recommended action
  - reason
  - markdown preview if stored in metadata
- [ ] Add test that `GET /api/approvals` includes pending review package decisions.

### 14. Update Frontend Types And Client

- [ ] Modify `web/src/types/api.ts`.
- [ ] Add:

```ts
export type ReviewDecisionStatus = "pending" | "approved" | "rejected" | string;

export type ReviewPackageDecision = {
  decision_id: string;
  package_id: string;
  scenario_id: string;
  workflow_id: string;
  baseline_run_id: string;
  candidate_run_ids: string[];
  recommended_action: string;
  status: ReviewDecisionStatus;
  reason: string;
  comment?: string | null;
  created_at: string;
  decided_at?: string | null;
  metadata: Record<string, unknown>;
};
```

- [ ] Modify `web/src/api/client.ts`.
- [ ] Add `submitReviewPackage`, `listReviewDecisions`, `approveReviewDecision`, `rejectReviewDecision`.
- [ ] Run `npm run build`.

### 15. Add Submit Button To Review Package UI

- [ ] Modify `web/src/features/evidence/EvidenceReviewPackage.tsx`.
- [ ] Add props:

```ts
onSubmit?: () => void;
submitDisabled?: boolean;
submitLoading?: boolean;
decision?: ReviewPackageDecision;
```

- [ ] Render:
  - “Submit for approval” button after package exists
  - pending/approved/rejected status if decision exists
  - no direct deployment wording
- [ ] Keep Markdown preview read-only.

### 16. Wire Submit In Evidence Run Detail Page

- [ ] Modify `web/src/features/evidence/EvidenceRunDetailPage.tsx`.
- [ ] Add `submitReviewPackage` mutation after package creation.
- [ ] Reason can be generated deterministically:

```text
Candidate package created from baseline/candidate evidence for human review.
```

- [ ] On success, show decision id and status.
- [ ] Invalidate approvals query if existing query key is used.
- [ ] Run `npm run build`.

### 17. Render Review Package Approval Detail

- [ ] Modify existing approval detail UI only if it currently assumes prompt proposal shape.
- [ ] For item type `evidence_review_package`, show:
  - baseline
  - candidates
  - recommended action
  - package reason
  - comment input
  - approve/reject buttons
- [ ] Do not show prompt patch diff for review package approvals.
- [ ] Add E2E expectations.

### 18. Extend Playwright E2E

- [ ] Modify `web/tests/e2e/console.spec.ts`.
- [ ] Mock:
  - `POST /api/evidence/review-packages/submit`
  - `GET /api/approvals`
  - `GET /api/approvals/{id}`
  - approve/reject if existing test route needs it
- [ ] Assert:
  - package is created
  - package is submitted
  - approval inbox shows review package item
  - approval detail does not render prompt-only fields
- [ ] Run `npm run e2e`.

### 19. Update Docs

- [ ] Modify `docs/core_innovation/impact_console.md`.
- [ ] Add section “Review Package Decision Flow”:

```text
Review package generated
  -> replay validation
  -> submit for approval
  -> approval inbox
  -> human approve/reject with comment
  -> decision memory
```

- [ ] Modify `docs/core_innovation/user_preference.md`.
- [ ] Clarify that human comments are preference evidence but do not auto-change policy.
- [ ] Modify `docs/business_lines/quant/README.md`.
- [ ] Add CLI example for package submit/decision.

### 20. Full Verification And Risk Review

- [ ] Run:

```bash
python -m unittest tests.evidence.test_review_package_decision_flow_next20 -v
python -m unittest tests.support.test_v58_web_api -v
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
find loop_harness tests scripts -name '__pycache__' -type d -prune -exec rm -rf {} +
find . -name '.DS_Store' -type f -delete
rm -rf .pytest_cache web/test-results web/playwright-report web/dist
```

- [ ] Run:

```bash
git diff --stat
git status --short
```

- [ ] Confirm scope stays in evidence decision flow, approval inbox bridge, API, UI, tests, and docs.
- [ ] Do not commit or push unless the user asks.

---

## Exit Criteria

This block is complete when:

1. Review packages can be submitted as pending human decisions.
2. Pending review package decisions appear in Approval Inbox.
3. Human approve/reject requires a comment.
4. Decisions are persisted and queryable by scenario/status.
5. Approval does not mutate any external workflow, prompt, publishing system, or trading system.
6. CLI/API/UI all expose the decision flow.
7. Tests and static checks pass, except environment-blocked E2E must be explicitly reported if local server binding is unavailable.

## Explicit Non-Goals

- No automatic deployment.
- No live trading or publishing.
- No prompt rewrite.
- No workflow builder.
- No TradingAgents adapter implementation.
- No policy self-relaxation based on one decision.
