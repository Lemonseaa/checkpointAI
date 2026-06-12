# Reference Projects

## Purpose

This file records projects LoopHarness should learn from.

It separates two categories:

```text
strategic references = learn product/architecture ideas, do not copy code
replacement wheels   = use mature external tools instead of rebuilding plumbing
```

This keeps LoopHarness focused:

```text
LoopHarness = external workflow evidence harness
```

It should not become another Dify, Nexent, Archon, Temporal, Prefect, or LiteLLM.

---

## Strategic References

These projects shape how LoopHarness thinks, but they are not direct code dependencies.

### Archon

Position:

```text
AI coding harness / workflow standardization layer
```

What:

Archon shows how AI work can be made repeatable by putting agents inside a workflow harness.
It treats workflow structure, verification, approvals, and execution context as first-class
engineering objects.

When to learn from it:

```text
When LoopHarness needs stronger workflow contract discipline:
- clear run stages
- deterministic verification steps
- approval gates
- reusable workflow skeletons
- adapter compatibility scoring before implementation
```

How it maps to LoopHarness:

```text
Archon executes structured AI workflows.
LoopHarness observes external workflows and judges whether changes improved them.
```

Not:

```text
Do not clone Archon as an AI coding workflow platform.
Do not make LoopHarness a YAML workflow runner just because Archon uses that shape.
```

### ARIS

Position:

```text
research loop methodology with adversarial review and audit trail
```

What:

ARIS is the most important reference for LoopHarness's evidence direction. It shows that
long-running AI systems need independent review, persistent artifacts, explicit claims, and
auditable reasoning instead of vague "self-improvement".

When to learn from it:

```text
When LoopHarness needs stronger evidence review:
- baseline/candidate comparison
- claim checking
- adversarial review
- handoff artifacts
- confidence boundaries
- rejection criteria for weak evidence
```

How it maps to LoopHarness:

```text
ARIS reviews research experiments.
LoopHarness reviews external workflow changes.
```

Not:

```text
Do not turn LoopHarness into a paper-writing or academic research tool.
Borrow the audit loop, not the domain.
```

### learn-harness-engineering

Position:

```text
harness engineering curriculum and design vocabulary
```

What:

The value is conceptual: a capable model is not enough; the harness around it determines
whether work becomes reproducible, verifiable, and safe.

When to learn from it:

```text
When deciding what belongs in LoopHarness and what should remain outside:
- instructions
- state
- verification
- scope
- lifecycle
```

How it maps to LoopHarness:

```text
It explains the discipline.
LoopHarness implements a narrow part of that discipline: evidence for external workflow changes.
```

Not:

```text
Do not copy course projects into the product.
Use it as a filter for architecture decisions.
```

### Nexent

Position:

```text
no-code / natural-language agent platform
```

What:

Nexent is a platform reference. It shows a possible end-user experience for generating agents,
connecting tools, managing memory, and versioning agent behavior.

When to learn from it:

```text
When designing UI/product experience:
- natural-language configuration
- agent versioning
- tool ecosystem integration
- personal knowledge boundaries
- workflow import visibility without becoming a workflow builder
```

How it maps to LoopHarness:

```text
Nexent helps users create and run agents.
LoopHarness helps users inspect and improve workflows that may come from Nexent-like systems.
```

Not:

```text
Do not compete with Nexent as a zero-code agent platform.
Do not build a full agent marketplace.
```

---

## Replacement Wheels

These projects are candidates for replacing old LoopHarness plumbing.

Detailed module mapping lives in:

```text
docs/borrowed_wheels/legacy_replacement_matrix.md
```

### APScheduler

Replaces:

```text
internal scheduler / interval jobs / cron-like logic
```

LoopHarness rule:

```text
Use APScheduler or cron when recurring local jobs are needed.
Do not expand loop_harness/scheduler as a platform.
```

### Temporal

Replaces:

```text
durable workflow execution / retries / HA failover
```

LoopHarness rule:

```text
Use Temporal only when durable workflow orchestration is truly needed.
Do not build HA orchestration inside LoopHarness.
```

### Prefect

Replaces:

```text
data/workflow orchestration for Python pipelines
```

LoopHarness rule:

```text
Reference or integrate with Prefect for pipeline execution.
LoopHarness should stay in the evidence and decision layer.
```

### LiteLLM

Replaces:

```text
full LLM provider platform / broad model routing / provider proxy
```

LoopHarness rule:

```text
Do not build a model console.
Use a thin adapter or LiteLLM-compatible layer when broad provider coverage is needed.
```

### MCP Servers

Replaces:

```text
custom plugin marketplace / generic tool ecosystem
```

LoopHarness rule:

```text
Use guarded MCP/tool connectors.
External tools are not trusted by default.
Sensitive side effects still require policy and human boundaries.

---

## Adapter Candidates

Use [Adapter Compatibility Checklist](adapter_checklist.md) before implementing
adapters for TradingAgents, Dify workflows, CrewAI, or custom scripts.

The first serious third-party candidate should be TradingAgents because quant
workflows can produce historical backtests, baseline/candidate metrics, and
repeatable evidence faster than content workflows.
```

---

## Decision Rule

Before adding a module, ask:

```text
Is this evidence, comparison, visualization, decision, or rollback?
```

If yes:

```text
Build it in LoopHarness.
```

If no:

```text
Find an external wheel, adapter, or reference pattern.
```
