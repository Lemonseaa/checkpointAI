# Risk Review

This document records product and architecture risks after the reset toward
external workflow evidence harnessing.

## Risk 1: Rebuilding Workflow Engines

Failure mode:

```text
Loop Harness starts adding scheduling, retries, DAG execution, plugin markets,
or agent runtime features again.
```

Control:

- Treat Dify, LangGraph, Archon, Temporal, Prefect, and custom scripts as
  workflow execution layers.
- Build adapters and evidence contracts, not another execution platform.
- Require new execution features to justify why an external wheel cannot be used.

## Risk 2: Optimizing Black Boxes

Failure mode:

```text
The system recommends prompt or strategy changes from input/output only.
```

Control:

- Mark missing trace and missing metrics as evidence gaps.
- Block optimization recommendations when critical evidence is missing.
- Require workflow graph and gap report in review packages.

## Risk 3: Cherry-Picked Optimization

Failure mode:

```text
UI shows only the best candidate and hides failed or weak candidates.
```

Control:

- Optimization charts must show weak, failed, and guardrail-breaking candidates.
- Reports must show evidence quality and sample count.
- Recommendations must say when evidence is inconclusive.

## Risk 4: Human Preference Drift

Failure mode:

```text
Agents infer permanent user preference from one approval comment or silently
rewrite the user's methodology.
```

Control:

- `user/USER_PROFILE.md` is human-written only.
- Hermes writes suggestions only to `SUGGESTED_PROFILE_NOTES.md`.
- Approval comments are evidence, not formal preference.

## Risk 5: False Autonomy

Failure mode:

```text
The system looks autonomous but only runs loops without proving improvement.
```

Control:

- Every action must connect to baseline, candidate, metric, evidence quality,
  risk, and rollback.
- Automatic action remains bounded by real evidence, policy, and decision logs.
- Review packages are required before high-impact changes.

## Risk 6: Duplicating Provider Platforms

Failure mode:

```text
Loop Harness becomes a broad LLM provider console.
```

Control:

- Use LiteLLM or provider SDKs if broad routing is needed.
- Keep internal provider abstraction thin.
- Provider choice is evidence metadata, not the product center.

## Risk 7: UI Scope Creep

Failure mode:

```text
The console becomes a workflow builder, code editor, database admin, or file
browser.
```

Control:

- UI focuses on Dashboard, Workflows, Evidence Review, Approvals, Charts,
  Preferences, Integrations, Reports, Backups.
- Workflow drafting is form-plus-language sketching only, not drag-and-drop
  execution design.

## Risk 8: Backtest Evidence Mistaken For Deployable Truth

Failure mode:

```text
A high-return historical candidate is treated as ready for paper trading or
live trading even though it has weak sample size, missing drawdown metrics, or
guardrail violations.
```

Control:

- Quant evidence must include `total_return`, `sharpe`, `max_drawdown`,
  `win_rate`, and `sample_count`.
- `max_drawdown` and `win_rate` are validated as ratios.
- Guardrail violations block paper-trading recommendation even when return or
  Sharpe improves.
- Review packages explicitly say whether paper trading is recommended and what
  human approval is required.

## Risk 9: TradingAgents Adapter Scope Creep

Failure mode:

```text
Loop Harness starts running or modifying TradingAgents before it can reliably
consume exported evidence.
```

Control:

- TradingAgents work starts as export-only conversion.
- The converter writes Workflow Contract v1 JSON and does not execute
  TradingAgents.
- Formal adapter implementation requires 5-10 real historical exports proving
  stable trace, metrics, config, artifacts, and prompt/config control surfaces.
- Live or paper trading remains human-gated and outside the converter.

## Current Decision

The next engineering work should prioritize:

1. Workflow map and graph polish.
2. Review package approval flow.
3. Optimization charts.
4. Human preference UI.
5. Quant evidence contract hardening.
6. TradingAgents export-only spike validation.
7. Adapter compatibility and gap reporting.

It should not prioritize:

1. New runtime abstractions.
2. More provider integrations.
3. More scheduler logic.
4. Plugin marketplace behavior.
5. Autonomous live deployment.
