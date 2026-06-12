# Borrowed Wheels

This folder records what LoopHarness should reuse, learn from, or avoid rebuilding.

The rule is strict:

```text
Do not rebuild mature plumbing unless it directly supports the evidence harness.
```

## Categories

- Strategic references: projects we learn from, but do not copy.
- Replacement wheels: mature tools that can replace old internal plumbing.
- Adapter checks: how to decide whether an external workflow is worth connecting.

## Current Files

- [WHEEL_STRATEGY.md](WHEEL_STRATEGY.md): what to reuse, borrow, own, or connect.
- [reference_projects.md](reference_projects.md): Archon, ARIS, learn-harness-engineering, Nexent, and replacement tools.
- [legacy_replacement_matrix.md](legacy_replacement_matrix.md): old module classification and cleanup order.
- [adapter_checklist.md](adapter_checklist.md): external adapter compatibility checklist.
