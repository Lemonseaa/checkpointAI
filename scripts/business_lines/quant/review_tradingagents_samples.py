"""Convert and review TradingAgents export samples without modifying sources."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").exists() and (parent / "loop_harness").is_dir()
)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loop_harness.evidence.tradingagents import convert_tradingagents_export  # noqa: E402
from loop_harness.evidence.tradingagents_compatibility import (
    score_tradingagents_samples,  # noqa: E402
)
from loop_harness.harness import EvidenceHarness  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    """Run a human-readable TradingAgents sample review drill."""

    parser = argparse.ArgumentParser(description="Review TradingAgents export samples through Loop Harness.")
    parser.add_argument("--input-dir", required=True, help="Directory containing TradingAgents-like JSON exports.")
    parser.add_argument("--db", default=".runtime/tradingagents_review.db", help="SQLite database for evidence review.")
    args = parser.parse_args(argv)

    input_dir = Path(args.input_dir)
    payloads = _convert_input_dir(input_dir)
    compatibility = score_tradingagents_samples(payloads)
    if not payloads:
        print("tradingagents_review converted=0 failed=all decision=no_go")
        return 1

    with TemporaryDirectory() as tmp:
        db_path = Path(args.db)
        harness = EvidenceHarness(db_path)
        for payload in payloads:
            harness.ingest_payload(payload)

        baseline_id = str(payloads[0]["run_id"])
        candidate_ids = [str(payload["run_id"]) for payload in payloads[1:]]
        if candidate_ids:
            package = harness.review_package_for_runs(baseline_id, candidate_ids)
            best_candidate = package.chart.best_candidate_run_id or "none"
            weakest_candidate = _weakest_candidate(package.chart.candidate_points)
            paper_ready = "yes" if package.recommended_action == "review_for_paper" else "no"
        else:
            best_candidate = "none"
            weakest_candidate = "none"
            paper_ready = "no"
        # Keep TemporaryDirectory alive through review construction; no source files are written.
        _ = tmp

    print(
        "tradingagents_review "
        f"converted={len(payloads)} "
        f"decision={compatibility.decision} "
        f"best_candidate={best_candidate} "
        f"weakest_candidate={weakest_candidate} "
        f"drawdown_blockers={_drawdown_blockers(payloads)} "
        f"sample_size_blockers={_sample_size_blockers(payloads)} "
        f"paper_trading_discussion_justified={paper_ready}"
    )
    return 0


def _convert_input_dir(input_dir: Path) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for path in sorted(input_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            print(f"conversion_skipped input={path} reason=not_object")
            continue
        try:
            payloads.append(convert_tradingagents_export(raw))
        except ValueError as exc:
            print(f"conversion_skipped input={path} reason={exc}")
    return payloads


def _weakest_candidate(points: object) -> str:
    if not isinstance(points, list) or not points:
        return "none"
    weakest = min(points, key=lambda point: point.objective_score if point.objective_score is not None else -999.0)
    return weakest.run_id


def _drawdown_blockers(payloads: list[dict[str, object]]) -> str:
    blockers: list[str] = []
    for payload in payloads:
        metrics = payload.get("metrics")
        if not isinstance(metrics, dict):
            continue
        drawdown = metrics.get("max_drawdown")
        if isinstance(drawdown, int | float) and float(drawdown) > 0.2:
            blockers.append(str(payload.get("run_id")))
    return ",".join(blockers) or "none"


def _sample_size_blockers(payloads: list[dict[str, object]]) -> str:
    blockers: list[str] = []
    for payload in payloads:
        metrics = payload.get("metrics")
        if not isinstance(metrics, dict):
            continue
        sample_count = metrics.get("sample_count")
        if isinstance(sample_count, int | float) and float(sample_count) < 30:
            blockers.append(str(payload.get("run_id")))
    return ",".join(blockers) or "none"


if __name__ == "__main__":
    raise SystemExit(main())
