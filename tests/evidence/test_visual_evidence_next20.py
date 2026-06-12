"""Visual evidence chart and quant CSV import tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from loop_harness.evidence.quant_drill import QuantDrillRunner
from loop_harness.harness import EvidenceHarness

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"


class VisualEvidenceNext20Test(unittest.TestCase):
    """Validate chartable optimization evidence and external CSV import."""

    def test_optimization_chart_marks_best_weak_and_guardrail_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = EvidenceHarness(Path(tmp) / "evidence.db")
            drill = QuantDrillRunner(harness.service)
            result = drill.run_v2(candidate_count=6, comparison_count=3)

            chart = harness.optimization_chart_for_runs(
                result.baseline_run_id,
                result.candidate_run_ids,
            )

            self.assertEqual(chart.baseline_run_id, result.baseline_run_id)
            self.assertEqual(chart.workflow_id, result.workflow_id)
            self.assertEqual(len(chart.candidate_points), 6)
            self.assertIn("sharpe", chart.chart_fields)
            self.assertTrue(any(point.best_candidate for point in chart.candidate_points))
            self.assertTrue(any(point.guardrail_status == "violated" for point in chart.candidate_points))
            self.assertTrue(any(point.candidate_quality == "weak" for point in chart.candidate_points))
            weak = next(point for point in chart.candidate_points if point.candidate_quality == "weak")
            self.assertEqual(weak.run_id, "quant_candidate_drill_weak")
            self.assertLess(weak.sharpe, 0.7)
            self.assertGreater(weak.max_drawdown, 0.2)
            self.assertIn("violated", chart.guardrail_summary)

    def test_quant_csv_import_creates_runs_and_chartable_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = EvidenceHarness(Path(tmp) / "evidence.db")
            result = harness.ingest_quant_csv(
                FIXTURE_DIR / "quant_backtest_results.csv",
                workflow_id="csv_quant_workflow",
                scenario_id="quant",
                run_kind="historical",
            )
            chart = harness.optimization_chart_for_runs("csv_baseline", result.run_ids[1:])

            self.assertEqual(result.imported_count, 3)
            self.assertEqual(result.run_ids, ["csv_baseline", "csv_candidate_strong", "csv_candidate_weak"])
            self.assertEqual(chart.baseline_run_id, "csv_baseline")
            self.assertEqual(len(chart.candidate_points), 2)
            self.assertTrue(any(point.run_id == "csv_candidate_strong" and point.best_candidate for point in chart.candidate_points))
            self.assertTrue(any(point.run_id == "csv_candidate_weak" and point.guardrail_status == "violated" for point in chart.candidate_points))
            stored = harness.store.get_run("csv_candidate_strong")
            self.assertIsNotNone(stored)
            self.assertEqual(stored.run.metadata["data_source"], "csv_import")  # type: ignore[union-attr]
            self.assertEqual(stored.run.scenario_id, "quant")  # type: ignore[union-attr]

    def test_evidence_chart_and_csv_cli_are_human_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "evidence.db"
            import_cmd = [
                sys.executable,
                "-m",
                "loop_harness.cli",
                "--db",
                str(db_path),
                "evidence",
                "import-quant-csv",
                "--path",
                str(FIXTURE_DIR / "quant_backtest_results.csv"),
                "--workflow",
                "csv_quant_workflow",
                "--scenario",
                "quant",
                "--kind",
                "historical",
            ]
            chart_cmd = [
                sys.executable,
                "-m",
                "loop_harness.cli",
                "--db",
                str(db_path),
                "evidence",
                "chart",
                "--baseline",
                "csv_baseline",
                "--candidate",
                "csv_candidate_strong",
                "--candidate",
                "csv_candidate_weak",
            ]

            imported = subprocess.run(import_cmd, check=True, capture_output=True, text=True)
            charted = subprocess.run(chart_cmd, check=True, capture_output=True, text=True)

            import_payload = json.loads(imported.stdout)
            chart_payload = json.loads(charted.stdout)
            self.assertEqual(import_payload["imported_count"], 3)
            self.assertIn("not_live_trading_evidence", import_payload["warning"])
            self.assertEqual(chart_payload["baseline_run_id"], "csv_baseline")
            self.assertTrue(any(item["guardrail_status"] == "violated" for item in chart_payload["candidate_points"]))


if __name__ == "__main__":
    unittest.main()
