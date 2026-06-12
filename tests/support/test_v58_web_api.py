"""V5.8 Web API contract tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from loop_harness import LoopHarness
from loop_harness.api import create_app
from loop_harness.auth import APIKeyManager
from loop_harness.console import BackupManager, CostEvent, CostEventStore
from loop_harness.decision import DecisionLogStore
from loop_harness.prompt import (
    PromptPatch,
    PromptProposal,
    PromptProposalStore,
    PromptSlot,
)
from loop_harness.scenario import Scenario, ScenarioStore


class V58WebApiTest(unittest.TestCase):
    """Validate the P0 Web API contract consumed by the React console."""

    def test_console_api_requires_auth_and_returns_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "web.db"
            self._create_scenario(db_path)
            client, token = self._client(db_path)

            unauthorized = client.get("/api/console/snapshot?scenario_id=quant")
            authorized = client.get(
                "/api/console/snapshot?scenario_id=quant",
                headers=self._auth(token),
            )

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized.status_code, 200)
        self.assertEqual(authorized.json()["scope"]["scenario_id"], "quant")
        self.assertEqual(authorized.json()["scenario_count"], 1)

    def test_approvals_can_be_listed_viewed_approved_and_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "web.db"
            proposal_id = self._create_prompt_proposal(db_path)
            client, token = self._client(db_path)

            listing = client.get("/api/approvals?scenario_id=quant", headers=self._auth(token))
            detail = client.get(f"/api/approvals/{proposal_id}", headers=self._auth(token))
            missing_comment = client.post(
                f"/api/approvals/{proposal_id}/approve",
                json={"comment": ""},
                headers=self._auth(token),
            )
            approve = client.post(
                f"/api/approvals/{proposal_id}/approve",
                json={"comment": "Evidence is enough for this demo."},
                headers=self._auth(token),
            )
            reject = client.post(
                f"/api/approvals/{proposal_id}/reject",
                json={"comment": "Reject after review."},
                headers=self._auth(token),
            )

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()[0]["source_id"], proposal_id)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["item_type"], "prompt_proposal")
        self.assertEqual(detail.json()["detail"]["patch"]["after"], "json")
        self.assertEqual(missing_comment.status_code, 400)
        self.assertEqual(approve.status_code, 200)
        self.assertTrue(approve.json()["updated"])
        self.assertEqual(reject.status_code, 404)

    def test_runs_scenarios_adapters_backups_and_health_are_exposed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "web.db"
            self._create_scenario(db_path)
            CostEventStore(db_path).record(
                CostEvent(
                    scenario_id="quant",
                    business_line_id="trading",
                    provider="minimax",
                    input_tokens=20,
                    output_tokens=10,
                    estimated_cost=0.03,
                )
            )
            backup = BackupManager(db_path, root / "backups").create_backup(label="before-api")
            client, token = self._client(db_path, backup_dir=root / "backups")
            headers = self._auth(token)

            scenarios = client.get("/api/scenarios", headers=headers)
            adapters = client.get("/api/adapters", headers=headers)
            run = client.post(
                "/api/runs",
                json={"scenario_id": "quant", "task": "analyze_signal", "context": {"symbol": "AAPL"}},
                headers=headers,
            )
            runs = client.get("/api/runs?scenario_id=quant", headers=headers)
            run_detail = client.get(f"/api/runs/{run.json()['run_id']}", headers=headers)
            backups = client.get("/api/backups", headers=headers)
            restore = client.post(
                f"/api/backups/{backup.id}/restore",
                json={"confirm": "RESTORE"},
                headers=headers,
            )
            health = client.get("/api/health", headers=headers)

        self.assertEqual(scenarios.status_code, 200)
        self.assertEqual(scenarios.json()[0]["id"], "quant")
        self.assertEqual(adapters.status_code, 200)
        self.assertTrue(any(adapter["name"] == "dummy_stock_signal" for adapter in adapters.json()))
        self.assertEqual(run.status_code, 200)
        self.assertEqual(run.json()["status"], "success")
        self.assertEqual(runs.status_code, 200)
        self.assertEqual(runs.json()[0]["scenario_id"], "quant")
        self.assertEqual(run_detail.status_code, 200)
        self.assertEqual(run_detail.json()["run_id"], run.json()["run_id"])
        self.assertEqual(backups.status_code, 200)
        self.assertEqual(backups.json()[0]["label"], "before-api")
        self.assertEqual(restore.status_code, 200)
        self.assertTrue(restore.json()["restored"])
        self.assertIn("pre_restore_backup_id", restore.json())
        self.assertEqual(health.status_code, 200)
        self.assertIn("overall_status", health.json())

    def test_evidence_api_ingests_lists_visualizes_reports_and_compares_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "web.db"
            client, token = self._client(db_path)
            headers = self._auth(token)

            baseline = client.post(
                "/api/evidence/runs",
                json=self._evidence_payload("baseline", 0.8),
                headers=headers,
            )
            candidate = client.post(
                "/api/evidence/runs",
                json=self._evidence_payload("candidate", 1.2),
                headers=headers,
            )
            runs = client.get("/api/evidence/runs?workflow_id=quant_backtest_v1", headers=headers)
            detail = client.get("/api/evidence/runs/candidate", headers=headers)
            visualization = client.get("/api/evidence/runs/candidate/visualization", headers=headers)
            report = client.get("/api/evidence/runs/candidate/report", headers=headers)
            workflow_map = client.get("/api/evidence/workflows/quant_backtest_v1/map", headers=headers)
            workflow_graph = client.get("/api/evidence/workflows/quant_backtest_v1/graph", headers=headers)
            run_graph = client.get("/api/evidence/runs/candidate/graph", headers=headers)
            gap_report = client.get("/api/evidence/runs/candidate/gaps", headers=headers)
            node_detail = client.get("/api/evidence/runs/candidate/nodes/strategy", headers=headers)
            goal_saved = client.post(
                "/api/evidence/goals/quant",
                json={
                    "primary_metrics": ["sharpe"],
                    "guardrail_metrics": ["max_drawdown"],
                    "max_cost_increase": 0.1,
                    "max_risk_level": "approval",
                    "preferences": {"trading_frequency": "low"},
                },
                headers=headers,
            )
            goal_loaded = client.get("/api/evidence/goals/quant", headers=headers)
            metric_schema_save = client.post(
                "/api/evidence/metrics/quant",
                json=[
                    {"name": "sharpe", "direction": "higher", "category": "business", "weight": 0.7},
                    {
                        "name": "max_drawdown",
                        "direction": "lower",
                        "category": "guardrail",
                        "weight": 0.3,
                        "threshold": 0.2,
                        "is_guardrail": True,
                    },
                ],
                headers=headers,
            )
            metric_schema_list = client.get("/api/evidence/metrics/quant", headers=headers)
            contract = client.post(
                "/api/evidence/contracts/validate",
                json=self._evidence_payload("contract-check", 1.0),
                headers=headers,
            )
            missing = client.get("/api/evidence/runs/missing-run", headers=headers)
            comparison = client.post(
                "/api/evidence/compare",
                json={"baseline_run_id": "baseline", "candidate_run_id": "candidate"},
                headers=headers,
            )
            workflow_chart = client.get(
                "/api/evidence/workflows/quant_backtest_v1/charts/optimization",
                headers=headers,
            )
            explicit_chart = client.post(
                "/api/evidence/charts/optimization",
                json={"baseline_run_id": "baseline", "candidate_run_ids": ["candidate"]},
                headers=headers,
            )
            review_package = client.post(
                "/api/evidence/review-packages",
                json={"baseline_run_id": "baseline", "candidate_run_ids": ["candidate"]},
                headers=headers,
            )
            review_package_validation = client.post(
                "/api/evidence/review-packages/validate",
                json=review_package.json(),
                headers=headers,
            )
            review_decision = client.post(
                "/api/evidence/review-packages/submit",
                json={"package": review_package.json(), "reason": "Candidate package is ready for review."},
                headers=headers,
            )
            review_decisions = client.get(
                "/api/evidence/review-decisions?scenario_id=quant&status=pending",
                headers=headers,
            )
            review_package_decision_status = client.get(
                f"/api/evidence/review-packages/{review_package.json()['package_id']}/decision",
                headers=headers,
            )
            approval_items = client.get("/api/approvals?scenario_id=quant", headers=headers)
            review_approval = client.get(
                f"/api/approvals/{review_decision.json()['decision_id']}",
                headers=headers,
            )
            review_approval_result = client.post(
                f"/api/approvals/{review_decision.json()['decision_id']}/approve",
                json={"comment": "Approved for paper review."},
                headers=headers,
            )
            approved_decisions = client.get(
                "/api/evidence/review-decisions?scenario_id=quant&status=approved",
                headers=headers,
            )
            direct_review_decision = client.post(
                "/api/evidence/review-packages/submit",
                json={"package": review_package.json(), "reason": "Second package is ready for direct API review."},
                headers=headers,
            )
            direct_reject = client.post(
                f"/api/evidence/review-decisions/{direct_review_decision.json()['decision_id']}/reject",
                json={"comment": "Rejected from direct endpoint for insufficient sample size."},
                headers=headers,
            )
            repeat_direct_reject = client.post(
                f"/api/evidence/review-decisions/{direct_review_decision.json()['decision_id']}/reject",
                json={"comment": "Rejecting twice should be a state conflict."},
                headers=headers,
            )
            decision_logs = DecisionLogStore(db_path).list(source_id=review_decision.json()["decision_id"])
            direct_decision_logs = DecisionLogStore(db_path).list(
                source_id=direct_review_decision.json()["decision_id"]
            )
            csv_import = client.post(
                "/api/evidence/import/quant-csv",
                json={
                    "path": str(Path(__file__).resolve().parents[1] / "fixtures" / "quant_backtest_results.csv"),
                    "workflow_id": "csv_quant_workflow",
                    "scenario_id": "quant",
                    "run_kind": "historical",
                },
                headers=headers,
            )
            comparison_export = client.post(
                "/api/evidence/compare/export",
                json={"baseline_run_id": "baseline", "candidate_run_id": "candidate"},
                headers=headers,
            )

        self.assertEqual(baseline.status_code, 200)
        self.assertEqual(baseline.json()["run_id"], "baseline")
        self.assertEqual(candidate.status_code, 200)
        self.assertEqual(runs.status_code, 200)
        self.assertEqual([row["run"]["run_id"] for row in runs.json()], ["baseline", "candidate"])
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["run"]["run_id"], "candidate")
        self.assertEqual(detail.json()["visualization"]["run_id"], "candidate")
        self.assertEqual(detail.json()["report"]["run_id"], "candidate")
        self.assertEqual(visualization.status_code, 200)
        self.assertEqual(visualization.json()["run_id"], "candidate")
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.json()["run_id"], "candidate")
        self.assertEqual(workflow_map.status_code, 200)
        self.assertEqual(workflow_map.json()["latest_run_id"], "candidate")
        self.assertEqual(workflow_graph.status_code, 200)
        self.assertEqual(workflow_graph.json()["run_id"], "candidate")
        self.assertEqual(run_graph.status_code, 200)
        self.assertEqual(run_graph.json()["workflow_id"], "quant_backtest_v1")
        self.assertIn("metric_sources", run_graph.json())
        self.assertEqual(gap_report.status_code, 200)
        self.assertIn("summary", gap_report.json())
        self.assertEqual(node_detail.status_code, 200)
        self.assertEqual(node_detail.json()["node_id"], "strategy")
        self.assertEqual(goal_saved.status_code, 200)
        self.assertEqual(goal_loaded.json()["primary_metrics"], ["sharpe"])
        self.assertEqual(metric_schema_save.status_code, 200)
        self.assertEqual(metric_schema_list.status_code, 200)
        self.assertEqual(metric_schema_list.json()[0]["name"], "max_drawdown")
        self.assertEqual(contract.status_code, 200)
        self.assertEqual(contract.json()["status"], "valid")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["code"], "evidence.run_not_found")
        self.assertEqual(comparison.status_code, 200)
        self.assertEqual(comparison.json()["recommendation"], "approve")
        self.assertEqual(workflow_chart.status_code, 200)
        self.assertEqual(workflow_chart.json()["baseline_run_id"], "baseline")
        self.assertEqual(explicit_chart.status_code, 200)
        self.assertEqual(explicit_chart.json()["candidate_points"][0]["run_id"], "candidate")
        self.assertEqual(review_package.status_code, 200)
        self.assertEqual(review_package.json()["baseline_run_id"], "baseline")
        self.assertEqual(review_package.json()["candidate_run_ids"], ["candidate"])
        self.assertEqual(review_package.json()["recommended_action"], "review_for_paper")
        self.assertIn("Evidence Review Package", review_package.json()["markdown"])
        self.assertEqual(review_package_validation.status_code, 200)
        self.assertTrue(review_package_validation.json()["valid"])
        self.assertEqual(review_decision.status_code, 200)
        self.assertEqual(review_decision.json()["status"], "pending")
        self.assertTrue(review_decision.json()["approval_required"])
        self.assertEqual(review_decisions.status_code, 200)
        self.assertEqual(review_decisions.json()[0]["decision_id"], review_decision.json()["decision_id"])
        self.assertEqual(review_package_decision_status.status_code, 200)
        self.assertEqual(review_package_decision_status.json()["status"], "pending")
        self.assertEqual(review_package_decision_status.json()["package_id"], review_package.json()["package_id"])
        self.assertEqual(approval_items.status_code, 200)
        self.assertIn("evidence_review_package", [item["item_type"] for item in approval_items.json()])
        self.assertEqual(review_approval.status_code, 200)
        self.assertEqual(review_approval.json()["item_type"], "evidence_review_package")
        self.assertEqual(review_approval_result.status_code, 200)
        self.assertTrue(review_approval_result.json()["updated"])
        self.assertEqual(approved_decisions.status_code, 200)
        self.assertEqual(approved_decisions.json()[0]["status"], "approved")
        self.assertEqual(decision_logs[0].kind.value, "approve")
        self.assertEqual(direct_review_decision.status_code, 200)
        self.assertEqual(direct_reject.status_code, 200)
        self.assertEqual(direct_reject.json()["status"], "rejected")
        self.assertEqual(repeat_direct_reject.status_code, 400)
        self.assertEqual(repeat_direct_reject.json()["code"], "evidence.review_decision_state_conflict")
        self.assertEqual(direct_decision_logs[0].kind.value, "reject")
        self.assertEqual(csv_import.status_code, 200)
        self.assertEqual(csv_import.json()["imported_count"], 3)
        self.assertEqual(comparison_export.status_code, 200)
        self.assertIn("Baseline vs Candidate", comparison_export.json()["report"])
        self.assertIn("candidate", comparison_export.json()["report"])

    def test_fallback_routes_include_console_api_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "web.db"
            app = create_app(
                loop_harness=LoopHarness(sqlite_path=db_path),
                auth_manager=APIKeyManager(),
                db_path=db_path,
                force_fallback=True,
            )

        paths = {route["path"] for route in app.routes}
        self.assertFalse(hasattr(app, "loop_harness"))
        self.assertIn("/api/console/snapshot", paths)
        self.assertIn("/api/evidence/runs", paths)
        self.assertIn("/api/evidence/runs/{run_id}", paths)
        self.assertIn("/api/evidence/runs/{run_id}/graph", paths)
        self.assertIn("/api/evidence/workflows/{workflow_id}/graph", paths)
        self.assertIn("/api/evidence/workflows/{workflow_id}/charts/optimization", paths)
        self.assertIn("/api/evidence/charts/optimization", paths)
        self.assertIn("/api/evidence/review-packages", paths)
        self.assertIn("/api/evidence/review-packages/validate", paths)
        self.assertIn("/api/evidence/review-packages/submit", paths)
        self.assertIn("/api/evidence/review-packages/{package_id}/decision", paths)
        self.assertIn("/api/evidence/review-decisions", paths)
        self.assertIn("/api/evidence/review-decisions/{decision_id}/approve", paths)
        self.assertIn("/api/evidence/review-decisions/{decision_id}/reject", paths)
        self.assertIn("/api/evidence/import/quant-csv", paths)
        self.assertIn("/api/evidence/compare", paths)
        self.assertIn("/api/approvals", paths)
        self.assertIn("/api/backups", paths)

    @staticmethod
    def _client(db_path: Path, backup_dir: Path | None = None) -> tuple[TestClient, str]:
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

    @staticmethod
    def _create_scenario(db_path: Path) -> None:
        ScenarioStore(db_path).save(
            Scenario(
                id="quant",
                name="Quant",
                description="Web API scenario",
                adapter_type="dummy_stock_signal",
                metadata={"domain_tags": ["quant"]},
            )
        )

    @staticmethod
    def _create_prompt_proposal(db_path: Path) -> str:
        proposal = PromptProposal(
            scenario_id="quant",
            agent_id="researcher",
            patch=PromptPatch(
                slot=PromptSlot.OUTPUT_FORMAT,
                operation="replace",
                before="text",
                after="json",
            ),
            reason="Improve structured evaluation.",
            expected_metric="sharpe",
        )
        PromptProposalStore(db_path).create(proposal)
        return proposal.id

    @staticmethod
    def _evidence_payload(run_id: str, sharpe: float) -> dict[str, object]:
        return {
            "workflow_id": "quant_backtest_v1",
            "run_id": run_id,
            "scenario_id": "quant",
            "run_kind": "historical",
            "nodes": [
                {"id": "load_data", "type": "data"},
                {"id": "strategy", "type": "agent"},
                {"id": "report", "type": "output"},
            ],
            "edges": [
                {"source": "load_data", "target": "strategy"},
                {"source": "strategy", "target": "report"},
            ],
            "trace": [
                {"node_id": "load_data", "status": "succeeded", "metrics": {"sample_count": 100}},
                {"node_id": "strategy", "status": "succeeded", "metrics": {"sharpe": sharpe}},
                {"node_id": "report", "status": "succeeded"},
            ],
            "metrics": {
                "sharpe": sharpe,
                "max_drawdown": 0.12,
                "sample_count": 100,
                "latency_ms": 300,
            },
            "metric_schema": {
                "sharpe": {"direction": "higher", "category": "business", "weight": 0.7},
                "max_drawdown": {
                    "direction": "lower",
                    "category": "guardrail",
                    "weight": 0.3,
                    "threshold": 0.2,
                    "is_guardrail": True,
                },
                "sample_count": {"direction": "higher", "category": "data_quality", "weight": 0.0},
                "latency_ms": {"direction": "lower", "category": "system", "weight": 0.0},
            },
        }


if __name__ == "__main__":
    unittest.main()
