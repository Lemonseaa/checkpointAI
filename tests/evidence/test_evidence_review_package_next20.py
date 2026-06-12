"""Evidence review package and replay validation tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from loop_harness.evidence.quant_drill import QuantDrillRunner
from loop_harness.harness import EvidenceHarness


class EvidenceReviewPackageNext20Test(unittest.TestCase):
    """Validate portable review packages for human/Hermes handoff."""

    def test_review_package_contains_graph_chart_comparisons_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = EvidenceHarness(Path(tmp) / "evidence.db")
            drill_result = QuantDrillRunner(harness.service).run_v2(candidate_count=6, comparison_count=3)

            package = harness.review_package_for_runs(
                drill_result.baseline_run_id,
                drill_result.candidate_run_ids,
            )

            self.assertTrue(package.package_id)
            self.assertEqual(package.baseline_run_id, drill_result.baseline_run_id)
            self.assertGreater(len(package.candidate_run_ids), 1)
            self.assertTrue(package.graph.summary)
            self.assertIn("violated", package.chart.guardrail_summary)
            self.assertEqual(len(package.comparison_reports), len(drill_result.candidate_run_ids))
            self.assertIn("Evidence Review Package", package.markdown)
            self.assertIn("Guardrail Summary", package.markdown)
            self.assertIn("Next Action", package.markdown)
            self.assertIn(package.recommended_action, package.markdown)

    def test_review_package_is_json_serializable_and_replay_validates_missing_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = EvidenceHarness(Path(tmp) / "evidence.db")
            drill_result = QuantDrillRunner(harness.service).run_v2(candidate_count=4, comparison_count=2)
            package = harness.review_package_for_runs(
                drill_result.baseline_run_id,
                drill_result.candidate_run_ids,
            )

            serialized = package.model_dump(mode="json")
            json.dumps(serialized)
            valid = harness.validate_review_package(package)
            baseline = harness.store.get_run(drill_result.baseline_run_id)
            assert baseline is not None
            missing = harness.service.validate_review_package_with_runs(
                package,
                [baseline],
            )

            self.assertTrue(valid.valid)
            self.assertFalse(missing.valid)
            self.assertIn(drill_result.candidate_run_ids[0], missing.missing_run_ids)

    def test_review_package_cli_outputs_json_markdown_and_replay_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "evidence.db"
            package_path = Path(tmp) / "package.json"
            seed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "loop_harness.cli",
                    "--db",
                    str(db_path),
                    "evidence",
                    "quant-drill",
                    "--v2",
                    "--candidates",
                    "4",
                    "--comparisons",
                    "2",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            seed_payload = json.loads(seed.stdout)
            package_cmd = [
                sys.executable,
                "-m",
                "loop_harness.cli",
                "--db",
                str(db_path),
                "evidence",
                "package",
                "--baseline",
                seed_payload["baseline_run_id"],
            ]
            for candidate_id in seed_payload["compared_candidate_ids"]:
                package_cmd.extend(["--candidate", candidate_id])

            packaged = subprocess.run(package_cmd, check=True, capture_output=True, text=True)
            package_json = json.loads(packaged.stdout)
            package_path.write_text(json.dumps(package_json), encoding="utf-8")
            markdown = subprocess.run(
                [*package_cmd, "--markdown"],
                check=True,
                capture_output=True,
                text=True,
            )
            replay = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "loop_harness.cli",
                    "--db",
                    str(db_path),
                    "evidence",
                    "replay-package",
                    "--path",
                    str(package_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("Evidence Review Package", package_json["markdown"])
            self.assertIn("Evidence Review Package", markdown.stdout)
            self.assertTrue(json.loads(replay.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
