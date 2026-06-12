# Demo Business Line

Demo evidence exists to validate Loop Harness contracts without depending on a
temporary sibling project.

The current built-in demo is `examples/evidence/quant_baseline_run.json` plus
`examples/evidence/quant_candidate_run.json`. It is a small quant-shaped
workflow with:

- structured nodes and edges;
- node-level trace;
- business, system, and data-quality metrics;
- strategy config surface;
- baseline/candidate comparison data.

It is intentionally not a live trading signal and not a dependency on
`opc_agent`.

## Rule

Demo adapters and fixtures exist to validate adapter contracts, not to become
product architecture.
