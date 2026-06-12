# Loop Harness Docs

This directory is organized by responsibility, not by historical version.

## Start Here

- [BLUEPRINT.md](BLUEPRINT.md): current product direction.
- [STRATEGIC_RESET_PLAN.md](STRATEGIC_RESET_PLAN.md): current execution plan.
- [SYSTEM_BOUNDARIES.md](SYSTEM_BOUNDARIES.md): boundaries between BusinessLine, Scenario, Policy, and legacy modules.

## Document Groups

```text
core_innovation/   Loop Harness's own differentiating system design.
borrowed_wheels/   Mature external projects and replacement strategy.
business_lines/    Business-specific applications and drills.
deployment/        Deployment and operations notes.
archive/           Historical architecture and research references.
superpowers/       Implementation plans created during development.
```

## Related Source Groups

```text
loop_harness/harness.py        Clean Evidence Harness facade.
loop_harness/evidence/        Current mainline code.
loop_harness/loop_harness.py  Compatibility facade for historical runtime paths.
tests/evidence/                Mainline evidence tests.
tests/business_lines/quant/    Quant business-line tests.
tests/support/                 Support regression tests.
tests/legacy/                  Historical compatibility tests.
examples/evidence/             Evidence input examples.
scripts/ops/                   Operational scripts.
scripts/business_lines/quant/  Quant business-line scripts.
```

## Rule

If a document describes what makes Loop Harness different, put it in `core_innovation/`.
If it describes external tools we borrow, learn from, or use to replace old code, put it in `borrowed_wheels/`.
If it describes quant, media, OPC demo, or another concrete domain, put it in `business_lines/`.
