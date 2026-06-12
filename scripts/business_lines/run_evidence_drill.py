"""Run a repeatable Evidence Harness drill for UI and approval validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").exists() and (parent / "loop_harness").is_dir()
)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loop_harness.evidence import (  # noqa: E402
    EvidenceBaselineStore,
    EvidenceService,
    EvidenceStore,
    QuantDrillResult,
    QuantDrillRunner,
)
from loop_harness.prompt import (  # noqa: E402
    Proposal,
    ProposalKind,
    ProposalPatch,
    ProposalStore,
    ProposalTargetType,
)


def main() -> None:
    """Run the evidence drill and print a human-readable summary."""

    parser = argparse.ArgumentParser(description="Run LoopHarness evidence drill.")
    parser.add_argument("--db", default="data/loopharness.db", help="SQLite database path.")
    parser.add_argument("--candidates", type=int, default=10, help="Number of candidate runs to generate.")
    args = parser.parse_args()

    db_path = Path(args.db)
    service = EvidenceService(EvidenceStore(db_path))
    result = QuantDrillRunner(service).run(candidate_count=args.candidates, comparison_count=min(5, args.candidates))
    baseline = EvidenceBaselineStore(db_path).set_baseline(
        workflow_id=result.workflow_id,
        baseline_run_id=result.baseline_run_id,
        reason="Evidence drill baseline.",
    )
    proposal_id = _create_best_proposal(db_path, result)

    print("evidence_drill_summary")
    print(f"workflow_id={result.workflow_id}")
    print(f"run_count={result.run_count}")
    print(f"baseline_run_id={baseline.baseline_run_id}")
    print(f"comparison_count={len(result.comparisons)}")
    print(f"proposal_id={proposal_id}")
    print(f"paper_trade_recommendation={result.paper_trade_recommendation}")
    print(f"summary={result.summary}")


def _create_best_proposal(db_path: Path, result: QuantDrillResult) -> str:
    best = max(
        result.comparisons,
        key=lambda report: report.comparison.objective_score if report.comparison is not None else -999.0,
    )
    proposal = Proposal(
        scenario_id="quant",
        proposal_kind=ProposalKind.EVIDENCE,
        target_type=ProposalTargetType.DEPLOYMENT,
        target_id=f"{result.workflow_id}:{best.candidate_run_id}",
        patch=ProposalPatch(
            operation="replace",
            before={"baseline_run_id": result.baseline_run_id},
            after={"candidate_run_id": best.candidate_run_id},
        ),
        reason=best.summary,
        expected_metric="objective_score",
        metadata={
            "workflow_id": result.workflow_id,
            "baseline_run_id": result.baseline_run_id,
            "candidate_run_id": best.candidate_run_id,
            "source": "evidence_drill",
        },
    )
    return ProposalStore(db_path).create(proposal)


if __name__ == "__main__":
    main()
