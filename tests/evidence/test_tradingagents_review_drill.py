"""TradingAgents sample review drill tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "tradingagents_like_run.json"
ROOT = Path(__file__).resolve().parents[2]


class TradingAgentsReviewDrillTest(unittest.TestCase):
    """Validate human-readable review output from TradingAgents sample exports."""

    def test_review_drill_outputs_human_summary_and_keeps_sources_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_dir = tmp_path / "input"
            input_dir.mkdir()
            baseline = _sample("ta_hist_baseline", sharpe=0.82, drawdown=0.15)
            candidate = _sample("ta_hist_candidate", sharpe=1.31, drawdown=0.11)
            baseline_path = input_dir / "baseline.json"
            candidate_path = input_dir / "candidate.json"
            baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            before = candidate_path.read_text(encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/business_lines/quant/review_tradingagents_samples.py",
                    "--input-dir",
                    str(input_dir),
                    "--db",
                    str(tmp_path / "review.db"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(candidate_path.read_text(encoding="utf-8"), before)
            self.assertIn("tradingagents_review", completed.stdout)
            self.assertIn("best_candidate=ta_hist_candidate", completed.stdout)
            self.assertIn("weakest_candidate=ta_hist_candidate", completed.stdout)
            self.assertIn("drawdown_blockers=none", completed.stdout)
            self.assertIn("sample_size_blockers=none", completed.stdout)
            self.assertIn("paper_trading_discussion_justified=yes", completed.stdout)


def _sample(run_id: str, *, sharpe: float, drawdown: float) -> dict[str, object]:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["run_id"] = run_id
    raw["run_kind"] = "historical"
    raw["metrics"] = {
        **raw["metrics"],
        "sharpe": sharpe,
        "max_drawdown": drawdown,
        "sample_count": 504,
    }
    return raw


if __name__ == "__main__":
    unittest.main()
