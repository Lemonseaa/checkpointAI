# TradingAgents Spike Go/No-Go Report

Status: `draft_template`

This report must be filled with real sanitized TradingAgents historical exports before formal adapter work starts.

## Sample Inventory

- Total exports reviewed:
- Real historical exports:
- Fixture/synthetic exports:
- Markets covered:
- Time ranges covered:
- Private data removed: yes/no

## Compatibility Score

- Decision: `go` / `needs_more_samples` / `needs_mapping_fix` / `no_go`
- Overall score:
- Input/output structure:
- Trace coverage:
- Business metrics:
- Config surface:
- Artifact quality:
- Prompt/control surface:
- Integration effort:

## Evidence Quality

- Core metrics present:
- Role or tool trace present:
- Strategy config present:
- Artifacts linked:
- Sample count sufficient:
- Fixture-only evidence present:

## Missing Fields

List every missing field that blocks adapter work:

- 

## Adapter Effort

- Estimated implementation days:
- Required upstream changes:
- Required Loop Harness changes:
- Dependencies:

## Risk Controls

- TradingAgents must remain external during spike review.
- Loop Harness must not place trades.
- Loop Harness must not modify TradingAgents internals.
- Live or paper trading decisions remain human-gated.
- Fixture-only evidence cannot justify optimization claims.

## Decision

Decision:

Reason:

Next action:

Formal TradingAgents adapter work can start only when this report says `go`, or `needs_mapping_fix` with explicit mapping fixes listed above.
