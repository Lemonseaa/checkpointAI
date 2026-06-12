# Core Innovation

This folder contains the parts Loop Harness should own.

Loop Harness's core innovation is not another Agent runtime. It is the evidence layer around external workflows:

```text
External workflow run
  -> workflow contract
  -> workflow visualization
  -> trace / metric coverage
  -> baseline vs candidate comparison
  -> evidence review
  -> human decision / rollback
```

## What Belongs Here

- Evidence Harness design.
- Workflow contract.
- Workflow visualization and black-box diagnosis.
- Impact Console for human evidence review.
- Metric schema and evidence review.
- Human methodology and preference boundaries.
- Approval, rollback, and decision evidence.

## What Does Not Belong Here

- External project summaries.
- Replacement wheels.
- Business-line-specific reports.
- Historical version acceptance notes.

## Current Files

- [metrics_reference.md](metrics_reference.md): metric direction, category, and comparison reference.
- [workflow_contract_v1.md](workflow_contract_v1.md): minimum external workflow evidence contract.
- [impact_console.md](impact_console.md): UI scope and Evidence API boundaries.
- [user_preference.md](user_preference.md): human-owned methodology, preference, and Hermes draft flow.
