"""Evidence review package decision flow tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from loop_harness.console import ApprovalInbox
from loop_harness.evidence.quant_drill import QuantDrillRunner
from loop_harness.harness import EvidenceHarness


class ReviewPackageDecisionFlowNext20Test(unittest.TestCase):
    """Validate human decision records for review packages."""

    def test_review_package_can_be_submitted_approved_and_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = EvidenceHarness(Path(tmp) / "evidence.db")
            drill_result = QuantDrillRunner(harness.service).run_v2(candidate_count=4, comparison_count=2)
            package = harness.review_package_for_runs(
                drill_result.baseline_run_id,
                drill_result.candidate_run_ids,
            )

            decision = harness.submit_review_package(package, reason="Candidate is ready for human review.")
            approved = harness.approve_review_package(decision.decision_id, comment="Approved for paper review.")
            listed = harness.list_review_package_decisions(scenario_id=package.scenario_id, status="approved")

            self.assertEqual(decision.package_id, package.package_id)
            self.assertEqual(decision.status.value, "pending")
            self.assertEqual(decision.scenario_id, package.scenario_id)
            self.assertEqual(decision.workflow_id, package.workflow_id)
            self.assertEqual(decision.baseline_run_id, package.baseline_run_id)
            self.assertEqual(decision.candidate_run_ids, package.candidate_run_ids)
            self.assertTrue(decision.approval_required)
            self.assertEqual(approved.status.value, "approved")
            self.assertEqual(approved.comment, "Approved for paper review.")
            self.assertEqual([item.decision_id for item in listed], [decision.decision_id])
            with self.assertRaises(ValueError):
                harness.reject_review_package(decision.decision_id, comment="Too late.")

    def test_review_decision_store_persists_filters_and_appears_in_approval_inbox(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = EvidenceHarness(Path(tmp) / "evidence.db")
            drill_result = QuantDrillRunner(harness.service).run_v2(candidate_count=3, comparison_count=1)
            package = harness.review_package_for_runs(
                drill_result.baseline_run_id,
                drill_result.candidate_run_ids,
            )

            decision = harness.submit_review_package(package, reason="Needs operator review.")
            pending = harness.list_review_package_decisions(scenario_id=package.scenario_id, status="pending")
            inbox_items = ApprovalInbox(harness.store.path).list_items(scenario_id=package.scenario_id)

            self.assertEqual([item.decision_id for item in pending], [decision.decision_id])
            self.assertIn("evidence_review_package", [item.item_type for item in inbox_items])
            self.assertEqual(
                next(item for item in inbox_items if item.item_type == "evidence_review_package").source_id,
                decision.decision_id,
            )

    def test_review_decision_cli_submit_list_and_decide(self) -> None:
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
            package_path.write_text(packaged.stdout, encoding="utf-8")

            submitted = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "loop_harness.cli",
                    "--db",
                    str(db_path),
                    "evidence",
                    "package-submit",
                    "--path",
                    str(package_path),
                    "--reason",
                    "Candidate package ready.",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            submitted_payload = json.loads(submitted.stdout)
            listed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "loop_harness.cli",
                    "--db",
                    str(db_path),
                    "evidence",
                    "package-decisions",
                    "--scenario",
                    "quant",
                    "--status",
                    "pending",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            decided = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "loop_harness.cli",
                    "--db",
                    str(db_path),
                    "evidence",
                    "package-decide",
                    "--id",
                    submitted_payload["decision_id"],
                    "--approve",
                    "--comment",
                    "Approved for paper review.",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertEqual(submitted_payload["status"], "pending")
            self.assertEqual(json.loads(listed.stdout)[0]["decision_id"], submitted_payload["decision_id"])
            self.assertEqual(json.loads(decided.stdout)["status"], "approved")


if __name__ == "__main__":
    unittest.main()
