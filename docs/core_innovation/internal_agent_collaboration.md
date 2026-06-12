# Internal Agent Collaboration

Loop Harness can use internal agents, but they should not become a second
workflow runtime. Their job is to inspect, explain, propose, and report around
external workflows.

## Design Rule

```text
External workflow agents do the business work.
Loop Harness internal agents produce evidence around that work.
```

Internal agents communicate through stored evidence objects:

- workflow contract
- graph payload
- gap report
- metric schema
- baseline/candidate comparison
- review package
- decision log
- user profile

They should not pass vague chat context as the main coordination mechanism.

## Roles

### Observer

Reads workflow runs, traces, artifacts, metrics, and logs.

Outputs:

- normalized evidence summary
- missing evidence list
- black-box node candidates

### Evaluator

Reads metric schema, baseline/candidate runs, evidence quality, and guardrails.

Outputs:

- objective comparison
- guardrail result
- evidence strength
- inconclusive reason when evidence is weak

### Proposer

Reads evaluation output and configurable surfaces.

Outputs:

- patch-first proposal
- expected metric
- reason
- risk notes

It does not rewrite entire workflows by default.

### Reviewer

Reads proposal, shadow/replay result, user profile, and historical decisions.

Outputs:

- review package summary
- approve/reject/continue-shadow recommendation
- unanswered questions

### Reporter

Turns stored evidence into human-readable reports and charts.

Outputs:

- run report
- comparison report
- review package markdown
- chart captions

## Coordination Pattern

Use a blackboard-style evidence store, not free-form agent chatter:

```text
External run
  -> Observer writes evidence
  -> Evaluator writes comparison
  -> Proposer writes proposal
  -> Reviewer writes review package
  -> Reporter writes human report
  -> Human decides
```

This gives the system a clear audit trail. Every agent output becomes a stored
artifact that can be inspected, rejected, replayed, or ignored.

## When To Use Voting

Voting is useful only for judgment-heavy review, such as:

- whether a proposal reason is convincing
- whether a content-style change matches the user profile
- whether evidence is too weak to act

Voting is not useful for deterministic checks such as schema validation,
metric direction, replay existence, or missing trace detection.

## When To Use Hive-Style Work

Hive-style parallel work is useful for independent analysis:

- multiple observers inspect different workflow nodes
- multiple evaluators inspect different metric groups
- multiple reviewers critique the same review package

It is dangerous for action execution. Actions must pass through policy, review
package, decision log, and rollback rules.

## Hard Boundaries

- Internal agents cannot mutate external workflows directly.
- Internal agents cannot modify `user/USER_PROFILE.md`.
- Internal agents cannot approve live trading, production publishing, or
  irreversible deployment.
- Internal agents cannot use weak synthetic evidence to justify automatic
  optimization.
