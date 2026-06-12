# Core Innovation

Loop Harness is not valuable because it can run agents. Other systems already
run agents and workflows well enough.

Loop Harness is valuable because it can make an external workflow visible,
measurable, reviewable, and improvable without becoming that workflow.

## Product Thesis

```text
External workflows create output.
Loop Harness proves whether workflow changes improve outcomes.
```

The product should stay centered on four capabilities.

## 1. Workflow Penetration

Loop Harness connects to a workflow and forces it to expose structure:

- nodes
- edges
- traces
- inputs and outputs
- metrics
- config surfaces
- artifacts
- errors
- cost and latency

The goal is not to draw a pretty graph. The goal is to answer:

```text
Where can this workflow be observed, evaluated, optimized, or rejected?
```

If a node has no trace, no output, no metric, or no configurable surface, it is
marked as a black box. The right next step is to improve observability, not to
pretend the system can optimize it.

## 2. Evidence Review Package

Humans should not approve scattered logs or isolated metrics. They should review
a complete package:

- workflow map
- baseline run
- candidate runs
- metric comparison
- guardrail result
- gap report
- replay / shadow validation
- recommended action
- reason and uncertainty

This is the primary decision object. A proposal is just a suggested change; an
evidence package explains whether the change is worth keeping.

## 3. Optimization Visualization

Every optimization claim needs a chart.

At minimum, the UI should show:

- baseline vs candidate metric deltas
- metric trend across runs
- guardrail movement
- cost / latency movement
- evidence quality and sample size

Charts are not decoration. They are the fastest way to see whether a claimed
improvement is real, noisy, or misleading.

## 4. Human Methodology Boundary

Loop Harness should learn from human decisions without taking over human taste,
methodology, or risk preference.

Human preferences live in user-owned files. Agents may summarize historical
approval comments and suggest updates, but the human writes or accepts the final
preference text.

This protects the system from slowly drifting into a style, strategy, or risk
profile the user never explicitly chose.

## Non-Goals

Loop Harness should not become:

- a workflow builder
- a coding-agent harness clone
- a Dify / Nexent clone
- a TradingAgents clone
- a broad LLM provider console
- an autonomous live trading or publishing system

Those are execution systems. Loop Harness is the control and evidence layer
around them.

## Success Standard

For any connected workflow, Loop Harness must eventually answer:

```text
1. What happened?
2. Where did it happen?
3. What changed?
4. Did the change improve the metric that matters?
5. Did it violate a guardrail?
6. Is the evidence strong enough?
7. What should the human do next?
```

If the system cannot answer those questions, it should say exactly what evidence
is missing.
