"""V5.11-V5.15 Web console hardening tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from loop_harness import LoopHarness
from loop_harness.api import create_app
from loop_harness.auth import APIKeyManager
from loop_harness.console import BackupManager
from loop_harness.demo import seed_console_demo


class V511V515ConsoleHardeningTest(unittest.TestCase):
    """Validate final V5 console APIs and operator guardrails."""

    def test_version_auth_reports_and_shadow_apis_are_exposed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "console.db"
            backup_dir = root / "backups"
            seeded = seed_console_demo(db_path, backup_dir)
            client, token = self._client(db_path, backup_dir)
            headers = self._auth(token)

            version = client.get("/api/version", headers=headers)
            auth = client.get("/api/auth/check", headers=headers)
            latest_report = client.get(
                "/api/reports/latest?scenario_id=demo-quant",
                headers=headers,
            )
            run_report = client.get(f"/api/reports/runs/{seeded['run_id']}", headers=headers)
            proposal_report = client.get(
                f"/api/reports/proposals/{seeded['proposal_id']}",
                headers=headers,
            )
            shadow_run = client.post(
                "/api/shadows",
                json={
                    "proposal_id": seeded["proposal_id"],
                    "task": "analyze_signal",
                    "context": {"symbol": "SPY"},
                    "config": {"run_kind": "synthetic"},
                },
                headers=headers,
            )
            shadows = client.get("/api/shadows?scenario_id=demo-quant", headers=headers)
            shadow_detail = client.get(f"/api/shadows/{shadow_run.json()['id']}", headers=headers)

        self.assertEqual(version.status_code, 200)
        self.assertEqual(version.json()["name"], "Loop Harness")
        self.assertEqual(auth.status_code, 200)
        self.assertTrue(auth.json()["authenticated"])
        self.assertEqual(latest_report.status_code, 200)
        self.assertIn("Run Report", latest_report.json()["report"])
        self.assertEqual(run_report.status_code, 200)
        self.assertIn(str(seeded["run_id"]), run_report.json()["report"])
        self.assertEqual(proposal_report.status_code, 200)
        self.assertIn("Proposal Report", proposal_report.json()["report"])
        self.assertEqual(shadow_run.status_code, 200)
        self.assertTrue(shadow_run.json()["is_shadow"])
        self.assertEqual(shadows.status_code, 200)
        self.assertEqual(shadows.json()[0]["proposal_id"], seeded["proposal_id"])
        self.assertEqual(shadow_detail.status_code, 200)
        self.assertEqual(shadow_detail.json()["id"], shadow_run.json()["id"])

    def test_restore_requires_explicit_confirmation_and_creates_safety_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "console.db"
            backup_dir = root / "backups"
            seed_console_demo(db_path, backup_dir)
            backup = BackupManager(db_path, backup_dir).create_backup(label="operator-check")
            client, token = self._client(db_path, backup_dir)
            headers = self._auth(token)

            missing_confirm = client.post(
                f"/api/backups/{backup.id}/restore",
                json={"confirm": "yes"},
                headers=headers,
            )
            restored = client.post(
                f"/api/backups/{backup.id}/restore",
                json={"confirm": "RESTORE"},
                headers=headers,
            )

        self.assertEqual(missing_confirm.status_code, 400)
        self.assertEqual(restored.status_code, 200)
        self.assertTrue(restored.json()["restored"])
        self.assertIsNotNone(restored.json()["pre_restore_backup_id"])

    @staticmethod
    def _client(db_path: Path, backup_dir: Path) -> tuple[TestClient, str]:
        manager = APIKeyManager()
        token = manager.generate_token("web")
        app = create_app(
            loop_harness=LoopHarness(sqlite_path=db_path),
            auth_manager=manager,
            db_path=db_path,
            backup_dir=backup_dir,
        )
        return TestClient(app), token

    @staticmethod
    def _auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    unittest.main()
