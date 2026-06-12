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
| TradingAgents | needs_spike | High-value quant target, but trace/metrics/config extraction must be proven before adapter code. |
| Dify workflow export/API | needs_spike | Useful ecosystem and UI reference, but node-level trace and metric capture vary by workflow. |
| CrewAI | needs_spike | Easier Python integration, but quality depends on how crews expose logs, tasks, and metrics. |
| Fully black-box SaaS workflow | no_go | Cannot support evidence-driven optimization without trace, metrics, or config surface. |

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

First improve observability, then integrate, then optimize.
