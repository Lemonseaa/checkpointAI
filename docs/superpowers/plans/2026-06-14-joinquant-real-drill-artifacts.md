# JoinQuant Real Drill Artifacts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make JoinQuant real-data drills persist reviewable JSON/Markdown artifacts and provide a deterministic fixture path for acceptance checks.

**Architecture:** Keep JoinQuant execution external. Loop Harness owns export diagnosis, optional normalization, evidence import, artifact writing, and human-readable reports. The CLI remains the operator entrypoint; no API or UI code is added in this step.

**Tech Stack:** Python, argparse CLI, Pydantic models, pytest/unittest, SQLite evidence harness.

---

## File Map

- Modify `loop_harness/quant_data/platform_export.py`: add artifact-writing helper and drill output paths to the summary.
- Modify `loop_harness/evidence/cli.py`: add `--output-json` and `--output-markdown` to `joinquant-real-drill`.
- Modify `tests/quant_data/test_platform_export.py`: test artifact writing at runner level.
- Modify `tests/quant_data/test_quant_data_cli.py`: test CLI artifact paths.
- Create `scripts/business_lines/quant/create_joinquant_fixture.py`: deterministic local JoinQuant batch fixture generator for manual acceptance.
- Create `tests/quant_data/test_joinquant_fixture_script.py`: verify fixture script and drill compatibility.
- Modify `examples/joinquant_exports/README.md`: document fixture generation and artifact outputs.
- Modify `docs/business_lines/quant/reports/joinquant_real_data_acceptance.md`: add artifact acceptance.

## 18-Step Execution

- [ ] 1. Add runner-level failing test for JSON/Markdown artifact writing.
- [ ] 2. Run the runner-level test and confirm it fails because artifact writing is missing.
- [ ] 3. Implement minimal runner artifact writing and summary output path fields.
- [ ] 4. Re-run runner-level test and confirm it passes.
- [ ] 5. Add CLI failing test for `--output-json` and `--output-markdown`.
- [ ] 6. Run the CLI test and confirm it fails because arguments are missing.
- [ ] 7. Implement CLI output path arguments and file writing call.
- [ ] 8. Re-run CLI test and confirm it passes.
- [ ] 9. Add failing fixture script test for deterministic JoinQuant sample batch generation.
- [ ] 10. Run fixture script test and confirm it fails because script is missing.
- [ ] 11. Implement fixture script with baseline and two candidate exports.
- [ ] 12. Re-run fixture script test and confirm it passes.
- [ ] 13. Add drill artifact command documentation to examples and acceptance docs.
- [ ] 14. Run quant test suite.
- [ ] 15. Run ruff.
- [ ] 16. Run mypy.
- [ ] 17. Run full unittest, compileall, and diff check.
- [ ] 18. Review `git diff --stat` and report remaining uncommitted scope.

