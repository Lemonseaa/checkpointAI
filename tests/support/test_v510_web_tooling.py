"""V5.10 console tooling tests."""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from loop_harness import LoopHarness
from loop_harness.api import create_app
from loop_harness.cli import main
from loop_harness.console import ApprovalInbox, BackupManager, ConsoleReadModel
from loop_harness.decision import DecisionKind, DecisionLogStore, DecisionRecord
from loop_harness.logs import SummaryLogStore
from loop_harness.scenario import ScenarioStore


class V510WebToolingTest(unittest.TestCase):
    """Validate web console operator tooling."""

    def test_api_serve_command_invokes_uvicorn_with_requested_options(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_run(app: str, **kwargs: object) -> None:
            calls.append({"app": app, **kwargs})

        with patch("loop_harness.api._uvicorn_server.run", fake_run):
            status = main(["api", "serve", "--host", "127.0.0.1", "--port", "8123", "--reload"])

        self.assertEqual(status, 0)
        self.assertEqual(calls[0]["app"], "loop_harness.api:create_app")
        self.assertEqual(calls[0]["host"], "127.0.0.1")
        self.assertEqual(calls[0]["port"], 8123)
        self.assertTrue(calls[0]["reload"])
        self.assertTrue(calls[0]["factory"])

    def test_seed_console_creates_human_actionable_demo_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "console.db"
            backup_dir = Path(tmp) / "backups"
            output = io.StringIO()

            with redirect_stdout(output):
                status = main(["--db", str(db_path), "demo", "seed-console", "--backup-dir", str(backup_dir)])

            snapshot = ConsoleReadModel(db_path).snapshot(
                scenario_id=None,
                allow_cross_scenario=True,
                reason="test",
            )
            scenarios = ScenarioStore(db_path).list()
            runs = SummaryLogStore(db_path).query_by_scenario("demo-quant")
            approvals = ApprovalInbox(db_path).list_items(scenario_id="demo-quant")
            backups = BackupManager(db_path, backup_dir).list_backups()

        self.assertEqual(status, 0)
        self.assertIn("Console demo seeded", output.getvalue())
        self.assertEqual(len(scenarios), 1)
        self.assertEqual(scenarios[0].id, "demo-quant")
        self.assertGreaterEqual(len(runs), 1)
        self.assertGreaterEqual(len(approvals), 1)
        self.assertGreaterEqual(len(backups), 1)
        self.assertEqual(snapshot.scenario_count, 1)
        self.assertGreaterEqual(snapshot.recent_run_count, 1)
        self.assertGreaterEqual(snapshot.pending_approval_count, 1)

    def test_api_app_accepts_initial_tokens_from_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "console.db"
            with patch.dict("os.environ", {"LOOPHARNESS_API_TOKENS": "dev-token, second-token"}):
                app = create_app(loop_harness=LoopHarness(sqlite_path=db_path), db_path=db_path)
            client = TestClient(app)

            response = client.get(
                "/api/health",
                headers={"Authorization": "Bearer dev-token"},
            )

        self.assertEqual(response.status_code, 200)

    def test_user_profile_api_is_readable_and_validates_human_updates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "console.db"
            with patch.dict("os.environ", {"LOOPHARNESS_API_TOKENS": "dev-token"}):
                app = create_app(loop_harness=LoopHarness(sqlite_path=db_path), db_path=db_path)
            client = TestClient(app)
            headers = {"Authorization": "Bearer dev-token"}

            profile = client.get("/api/user-profile", headers=headers)
            missing_reason = client.post(
                "/api/user-profile",
                json={"content": "# User Profile\n\nHuman confirmed."},
                headers=headers,
            )

        self.assertEqual(profile.status_code, 200)
        self.assertIn("formal_profile", profile.json())
        self.assertIn("suggested_notes", profile.json())
        self.assertEqual(missing_reason.status_code, 400)
        self.assertEqual(missing_reason.json()["code"], "user_profile.missing_field")

    def test_user_profile_suggestion_uses_decisions_without_modifying_formal_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "console.db"
            DecisionLogStore(db_path).record(
                DecisionRecord(
                    source_id="review-1",
                    source_type="evidence_review_package",
                    kind=DecisionKind.APPROVE,
                    scenario_id="quant",
                    actor="human",
                    action="approve_review_package",
                    comment="Prefer lower drawdown before paper trading.",
                )
            )
            with patch.dict("os.environ", {"LOOPHARNESS_API_TOKENS": "dev-token"}):
                app = create_app(loop_harness=LoopHarness(sqlite_path=db_path), db_path=db_path)
            client = TestClient(app)
            headers = {"Authorization": "Bearer dev-token"}

            before = client.get("/api/user-profile", headers=headers)
            suggestion = client.post("/api/user-profile/suggest", json={"scenario_id": "quant"}, headers=headers)
            after = client.get("/api/user-profile", headers=headers)

        self.assertEqual(suggestion.status_code, 200)
        self.assertIn("Prefer lower drawdown before paper trading.", suggestion.json()["content"])
        self.assertEqual(after.json()["suggested_notes"], suggestion.json()["content"])
        self.assertEqual(after.json()["formal_profile"], before.json()["formal_profile"])


if __name__ == "__main__":
    unittest.main()
