# Impact Console

Impact Console is the human control surface for the Evidence Harness.

It is not a workflow builder, code editor, file browser, model console, or Agent marketplace.

## Primary Job

The console answers:

```text
What changed?
What evidence exists?
Did the candidate beat the baseline?
Where is the workflow still black-box?
Should the human approve, reject, continue shadow, or roll back?
```

## Primary API

New UI work should start from the Evidence Harness API:

```text
POST /api/evidence/runs
GET  /api/evidence/runs?workflow_id=...
GET  /api/evidence/workflows/{workflow_id}/map
GET  /api/evidence/workflows/{workflow_id}/graph
GET  /api/evidence/workflows/{workflow_id}/charts/optimization
GET  /api/evidence/runs/{run_id}/visualization
GET  /api/evidence/runs/{run_id}/graph
GET  /api/evidence/runs/{run_id}/report
GET  /api/evidence/runs/{run_id}/gaps
GET  /api/evidence/runs/{run_id}/nodes/{node_id}
POST /api/evidence/compare
POST /api/evidence/compare/export
POST /api/evidence/charts/optimization
POST /api/evidence/review-packages
POST /api/evidence/review-packages/validate
POST /api/evidence/import/quant-csv
```

Older `/api/runs` and scenario adapter routes are compatibility/control-console paths.
They should not become the main workflow visualization path.

## P0 Screens

```text
Dashboard
Workflows / workflow map
Evidence run list
Workflow visualization
Baseline vs candidate comparison
Evidence report
Approval inbox
Optimization charts
Rollback / backup entry
```

The full UI information architecture is maintained in
[ui_information_architecture.md](ui_information_architecture.md). This file
only records the Impact Console's evidence and API boundaries.

## Baseline Comparison View

The comparison view must show optimization impact visually, not only as JSON.

Minimum evidence:

```text
Baseline run
Candidate run
Recommendation
Human-readable summary
Business metric delta
System metric delta
Data quality metric delta
Evidence quality
Approval proposal entry
```

The UI may render simple bars before introducing a charting library.
The important rule is that the human can see whether the candidate improved,
what got worse, and whether the evidence is clean enough to trust.

## Visual Proof Before Optimization

When metrics exist, every claimed improvement should have a chartable before
and after view. The console should show at least:

```text
baseline run
candidate runs
best candidate marker
business metric movement
guardrail violations
weak candidates
current run highlight
```

This rule prevents the system from showing only successful examples. A useful
optimization console must make bad candidates visible too, especially candidates
that improve one metric while violating risk boundaries.

## Workflow Visualization View

Workflow visualization is an observability surface.
It shows how an external workflow actually ran; it does not edit the workflow.

Minimum evidence:

```text
Node labels
Execution path
Trace coverage
Metric coverage
Black-box nodes
Error nodes
Node latency
Node cost
Input/output summary
Optimization eligibility
Next action summary
Pinned baseline marker
```

The current graph payload is deterministic and UI-ready. It includes layout,
filters, metric sources, gap markers, optimization eligibility, and proposal
targeting metadata. Graph libraries are optional; the product requirement is
that the human can see which part of the workflow produced evidence and which
part remains a black box.

## Approval Bridge

When a candidate beats a pinned baseline and evidence quality is not rejected,
the console may create an approval proposal.

This proposal is still a review artifact:

```text
no external workflow mutation
no live deployment
no automatic publishing
no live trading
```

The proposal must include baseline id, candidate id, metric deltas, and quality status.

## Review Package Handoff

The review package is the compact artifact for human or Hermes review.

It bundles:

```text
workflow graph
optimization chart
baseline id
candidate ids
comparison reports
evidence gaps
recommended next action
Markdown summary
```

The package is generated from stored evidence. It is not manually edited and it
does not mutate prompts, strategies, workflows, trading systems, or publishing
systems.

Before acting on a package, the console or CLI can replay-validate it against
SQLite:

```text
POST /api/evidence/review-packages/validate
loopharness evidence replay-package --path package.json
```

Replay validation answers whether the referenced runs still exist and whether
the charted metric keys still match stored evidence. This keeps review grounded
in reproducible evidence rather than screenshots or copied notes.

## Review Package Decision Flow

Review packages become actionable only after explicit human submission:

```text
review package generated
  -> replay validation
  -> submit for approval
  -> Approval Inbox
  -> human approve/reject with comment
  -> decision log and decision memory evidence
```

Approval means “this package is accepted as a review decision.” It does not mean
deployment.

The decision record stores:

```text
package id
workflow id
scenario id
baseline id
candidate ids
recommended action
human reason
human approval/rejection comment
```

These records are useful training and preference evidence. They are not
permission for automatic policy relaxation or live action.

## Hard Boundaries

```text
No drag-and-drop workflow builder
No direct code editing
No direct database editing
No plugin marketplace
No full model provider console
No automatic live trading or publishing approval
```
