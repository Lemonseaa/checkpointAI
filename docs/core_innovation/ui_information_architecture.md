# UI Information Architecture

Loop Harness UI is a control console.

It is not a workflow builder, code editor, file browser, database admin, model
provider console, or plugin marketplace.

## Primary Navigation

```text
Dashboard
Workflows
Evidence Review
Approvals
Charts
Preferences
Integrations
Reports
Backups
Settings
```

## Dashboard

Purpose:

```text
Show what needs attention now.
```

Minimum cards:

- active scenarios
- recent runs
- pending approvals
- evidence packages awaiting review
- weak evidence count
- cost summary
- system health

## Workflows

Purpose:

```text
Make external workflows visible.
```

Views:

- workflow list
- workflow map
- node inspector
- black-box report
- trace coverage
- metric coverage
- configurable surfaces

This is the most important product surface after approvals. It proves Loop
Harness is not just reading inputs and outputs; it is penetrating the workflow.

## Evidence Review

Purpose:

```text
Give the human one complete decision object.
```

Views:

- baseline run
- candidate runs
- workflow graph
- optimization chart
- comparison table
- guardrail result
- gap report
- replay/shadow validation
- recommended action

## Approvals

Purpose:

```text
Centralize human decisions.
```

Approval detail must answer:

- what changed
- why it changed
- what evidence supports it
- what got better
- what got worse
- what risk remains
- how to roll back
- what similar historical decisions say

## Charts

Purpose:

```text
Show whether optimization actually improved outcomes.
```

Required charts:

- baseline vs candidate
- metric trend across runs
- guardrail movement
- cost / latency movement
- evidence quality
- weak and failed candidates

Charts must show bad and inconclusive candidates, not only winners.

## Preferences

Purpose:

```text
Let the human define methodology, taste, and risk boundaries.
```

The UI can show:

- `USER_PROFILE.md`
- Hermes suggested notes
- approval comment history
- profile version history

The UI must not provide one-click “apply Hermes suggestion” unless the human can
review and edit the final text first.

## Integrations

Purpose:

```text
Show what external wheels are connected.
```

Views:

- adapter list
- capabilities
- compatibility report
- required evidence gaps
- last successful run

This page configures connectors, not workflow internals.

## Workflow Drafting

Loop Harness may eventually help users draft personalized workflows from
language and forms.

This is not a drag-and-drop builder.

The first version should be a structured intake:

- business goal
- available data
- target metric
- guardrails
- required human checkpoints
- external tools available
- preferred collaboration style
- forbidden actions

The output is:

- workflow sketch
- recommended external wheels
- required adapters
- evidence contract
- first validation plan

The sketch must be reviewable before it becomes a runnable workflow.

## Not In UI

- direct code editing
- direct database editing
- raw file browser
- model marketplace
- plugin marketplace
- policy rule editor for unsafe autonomy
- live deployment button without review package and explicit confirmation
