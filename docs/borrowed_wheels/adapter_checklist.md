# Adapter Compatibility Checklist

## Purpose

Decide whether an external Agent framework or workflow is worth adapting before
writing adapter code.

Loop Harness should not spend engineering time on workflows that cannot expose
evidence. This checklist exists to answer:

```text
Should we even try to adapt this workflow?
```

## Required Evaluation Artifact

Every third-party adapter candidate should produce a short compatibility
report with:

- candidate name and repository;
- intended scenario;
- checklist scores;
- blockers;
- estimated integration effort;
- go / needs_spike / no_go decision.

## Scoring

Score each item from 0 to 2:

```text
0 = missing or unusable
1 = partially available or requires wrapper work
2 = available and structured enough for Loop Harness
```

| Area | Field | Why It Matters | Required |
|---|---|---|---|
| Input/Output | Structured input | Loop Harness needs repeatable task/context input. | Yes |
| Input/Output | Structured output | Output must be machine-readable, not only prose. | Yes |
| Workflow Map | Nodes and edges | Needed for workflow visualization. | Yes |
| Trace | Node-level trace | Needed to avoid black-box optimization. | Yes |
| Metrics | Business metrics | Needed for baseline/candidate comparison. | Yes |
| Metrics | System metrics | Needed for latency/cost/regression diagnosis. | Preferred |
| Config Surface | Parameters exposed | Needed to know what changed. | Yes |
| Prompt Control | Prompt slots exposed | Needed for prompt optimization. | Preferred |
| Execution | Replay or shadow run | Needed before applying risky changes. | Preferred |
| Artifacts | Reports/logs/files linkable | Needed for audit and review. | Preferred |
| Isolation | Scenario/data separation | Needed to prevent cross-domain contamination. | Yes |
| Effort | Estimated integration days | Prevents sunk-cost adapters. | Yes |
| Dependencies | External services required | Determines operational burden. | Yes |

## Decision Rules

`no_go` when any of these are true:

- structured input is missing;
- structured output is missing;
- workflow map cannot be reconstructed;
- no business metric is available;
- config surface is unavailable and the workflow is not explicitly observation-only;
- integration requires modifying a large external framework before any evidence can be produced.

`needs_spike` when any of these are true:

- node-level trace is unclear;
- metrics exist but require parsing unstructured text;
- shadow/replay is unclear;
- estimated integration effort is more than 5 days;
- external dependencies are heavy or unstable;
- the workflow is promising but the evidence contract is not yet proven.

`go` only when:

- no required blocker exists;
- total score is at least 75%;
- a sample run can be converted to Workflow Contract v1;
- the first adapter can produce at least one baseline/candidate comparison.

## Candidate Snapshot

| Candidate | Current Decision | Reason |
|---|---|---|
| Built-in quant evidence demo | go | First-party fixture already exposes nodes, trace, metrics, config, and baseline/candidate data. |
| TradingAgents | needs_spike | High-value quant target. Export-only conversion is feasible, but real run trace and metric extraction must be proven before a formal adapter. |
| Dify workflow export/API | needs_spike | Useful ecosystem and UI reference, but node-level trace and metric capture vary by workflow. |
| CrewAI | needs_spike | Easier Python integration, but quality depends on how crews expose logs, tasks, and metrics. |
| Fully black-box SaaS workflow | no_go | Cannot support evidence-driven optimization without trace, metrics, or config surface. |

## TradingAgents Spike Report

Candidate: TradingAgents-style quant research workflow
Repository / source: external TradingAgents-compatible export, not directly imported
Scenario: quant
Use case: historical backtest evidence converted into Workflow Contract v1

Scores:

- Structured input: 1 — task metadata can be represented, but exact upstream API varies.
- Structured output: 1 — feasible if a JSON export is produced; Markdown-only output is insufficient.
- Workflow map: 1 — roles can be mapped into nodes and sequence edges.
- Node trace: 1 — role-level summaries and duration/cost are enough for a first map, but tool-level trace still needs proof.
- Business metrics: 2 — backtest metrics map cleanly when exported as numbers.
- System metrics: 1 — latency/cost can be captured when role timings are exported.
- Config surface: 2 — strategy parameters map to `config`.
- Prompt control: 0 — prompt slots are not proven in this spike.
- Replay / shadow: 1 — exported historical runs can be replayed through Loop Harness, but TradingAgents execution is not controlled.
- Artifacts: 2 — reports/log files can be linked as artifacts.
- Isolation: 1 — scenario/run IDs provide Loop Harness isolation; upstream data isolation still needs review.
- Effort: 1 — export-only conversion is small; formal adapter depends on upstream instrumentation.
- Dependencies: 1 — no dependency for export conversion; full integration may require TradingAgents runtime setup.

Blockers:

- Tool-level trace is not proven.
- Prompt/control surfaces are not proven.
- Fixture-only evidence is not enough for a go decision.
- Direct execution should not be added before export-quality evidence is stable.

Estimated integration effort:

```text
export-only spike: 0.5-1 day
formal adapter after real samples: 3-5 days
```

Decision: needs_spike

Reason:

TradingAgents is worth investigating, but Loop Harness should first consume
exported JSON evidence. A formal adapter is justified only after at least one
real TradingAgents run can expose stable metrics, config, trace, and artifacts.

Adapter approval is now based on `score_tradingagents_samples(converted_payloads)`,
not repository reputation or fixture success. The score must use sanitized real
historical exports:

- Fixture-only samples produce `no_go`.
- Fewer than five real exports produce `needs_more_samples`.
- Missing trace, config surface, or core quant metrics produce `needs_mapping_fix`.
- Only enough real, structured samples can produce `go`.

## Report Template

```text
Candidate:
Repository / source:
Scenario:
Use case:

Scores:
- Structured input:
- Structured output:
- Workflow map:
- Node trace:
- Business metrics:
- System metrics:
- Config surface:
- Prompt control:
- Replay / shadow:
- Artifacts:
- Isolation:
- Effort:
- Dependencies:

Blockers:

Estimated integration effort:

Decision: go / needs_spike / no_go

Reason:
```

## Rule

Write the compatibility report before writing adapter code.

For TradingAgents, formal adapter implementation can start only after
`docs/business_lines/quant/reports/tradingagents_spike_go_no_go.md` is filled
from real sanitized exports and says `go`, or `needs_mapping_fix` with explicit
fixes.

First improve observability, then integrate, then optimize.
