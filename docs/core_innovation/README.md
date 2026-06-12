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

- [CORE_INNOVATION.md](CORE_INNOVATION.md): product thesis and the owned innovation surface.
- [metrics_reference.md](metrics_reference.md): metric direction, category, and comparison reference.
- [workflow_contract_v1.md](workflow_contract_v1.md): minimum external workflow evidence contract.
- [workflow_visualization_model.md](workflow_visualization_model.md): graph payload and black-box visualization model.
- [charts_api.md](charts_api.md): chart payloads for optimization evidence.
- [internal_agent_collaboration.md](internal_agent_collaboration.md): internal Observer/Evaluator/Proposer/Reviewer/Reporter model.
- [ui_information_architecture.md](ui_information_architecture.md): UI navigation and product surface boundaries.
- [impact_console.md](impact_console.md): UI scope and Evidence API boundaries.
- [user_preference.md](user_preference.md): human-owned methodology, preference, and Hermes draft flow.
