# Wheel Strategy

Loop Harness should stay small where mature wheels already exist, and be deep
only where the product is genuinely different.

## Rule

```text
Use mature wheels for execution plumbing.
Own the evidence, visualization, review, and decision layer.
```

Every new module must answer four questions before it is built:

1. What existing project already solves this?
2. Why is that project not enough for the evidence harness?
3. Is this a core capability, a connector, or a temporary compatibility layer?
4. How will this be deleted if a better wheel replaces it?

## Directly Reuse

These areas should use external projects or system tools instead of internal
platform code.

| Area | Preferred Wheel | Loop Harness Role |
|---|---|---|
| Workflow execution | Dify, LangGraph, Archon, Temporal, Prefect | Ingest their run evidence; do not clone their engines. |
| Agent teams | TradingAgents-style systems, CrewAI, custom scripts | Treat them as external workflows behind adapters. |
| Tools and plugins | MCP servers, Dify plugins, existing GitHub tools | Connect through guarded adapters; do not build a plugin marketplace. |
| LLM provider routing | LiteLLM or provider SDKs | Use a thin provider boundary only when evidence collection needs it. |
| Scheduling | cron, APScheduler, external orchestrators | Trigger evidence runs; do not build a durable scheduler platform. |
| Deployment | Docker, cloud infra, managed databases | Document deployment; do not build HA platform logic in core. |

## Borrow Ideas

These projects are references, not dependencies.

| Project | Borrow | Do Not Borrow |
|---|---|---|
| Archon | Deterministic harness nodes, approval gates, reproducible runs | Full coding workflow platform. |
| ARIS | Evidence loop, adversarial review, audit trail | Academic paper pipeline specifics. |
| learn-harness-engineering | Instructions, state, verification, scope, lifecycle discipline | Course structure as product architecture. |
| Nexent | Natural-language agent creation, versioning, rollback UX | Full no-code agent platform or marketplace. |
| Dify | Fast workflow prototyping, plugin ecosystem, visual inspiration | Node-builder as Loop Harness's core product. |
| TradingAgents | Role decomposition for quant research | Internal trading runtime clone. |

## Own

Loop Harness should own these because they define the product:

- Workflow evidence contract.
- Workflow visualization and black-box diagnosis.
- Baseline-vs-candidate comparison with metric direction and categories.
- Evidence review package.
- Human approval inbox for evidence-backed decisions.
- Decision log and rollback trail.
- Human-owned methodology / preference profile.
- Charts that show whether an optimization actually improved outcomes.

## Connectors

Connectors are thin and replaceable. They should:

- Accept or produce `WorkflowContract` shaped data.
- Preserve raw external outputs for audit.
- Mark missing trace, metrics, or config as gaps instead of pretending.
- Avoid importing unstable internal packages from demo projects.
- Be removable without changing the core evidence model.

## Rejection Rule

If a proposed feature mostly improves execution, scheduling, provider routing,
tool management, or deployment, assume it belongs to an external wheel until
proven otherwise.

If a proposed feature improves observability, evidence quality, comparison,
human review, rollback confidence, or visual understanding, it may belong in
Loop Harness.
