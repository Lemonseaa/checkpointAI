"""Workflow contract, map, gap, goal, and decision-memory tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from loop_harness.decision import DecisionKind, DecisionLogStore, DecisionRecord
from loop_harness.evidence import EvidenceService, EvidenceStore
from loop_harness.evidence.boundary import CandidateBoundary, CandidateChange
from loop_harness.evidence.contract import WorkflowContractValidator
from loop_harness.evidence.decision_memory import HumanDecisionMemory
from loop_harness.evidence.goal import OptimizationGoalProfile, OptimizationGoalStore
from loop_harness.evidence.trace import TraceNormalizer


def _payload(run_id: str = "candidate") -> dict[str, object]:
    return {
        "workflow_id": "quant_flow",
        "run_id": run_id,
        "scenario_id": "quant",
        "run_kind": "historical",
        "nodes": [
            {"id": "ingest", "type": "data", "metadata": {"config_surface": "data_window"}},
            {"id": "researcher", "type": "agent", "metadata": {"optimizable": True}},
            {"id": "broker", "type": "external", "metadata": {"black_box": True}},
            {"id": "report", "type": "output"},
        ],
        "edges": [
            {"source": "ingest", "target": "researcher"},
            {"source": "researcher", "target": "broker"},
            {"source": "researcher", "target": "report"},
        ],
        "trace": [
            {
                "node_id": "ingest",
                "status": "succeeded",
                "duration_ms": 100,
                "metrics": {"sample_count": 120},
                "input_summary": "AAPL historical bars",
                "output_summary": "120 daily bars",
            },
            {
                "node_id": "researcher",
                "status": "succeeded",
                "duration_ms": 300,
                "cost": 0.04,
                "metrics": {"sharpe": 1.2},
                "input_summary": "bars + config",
                "output_summary": "moving average signal",
            },
            {"node_id": "report", "status": "succeeded", "duration_ms": 50},
        ],
        "metrics": {"sharpe": 1.2, "max_drawdown": 0.13, "sample_count": 120, "latency_ms": 450},
        "metric_schema": {
            "sharpe": {"direction": "higher", "category": "business", "weight": 0.7},
            "max_drawdown": {"direction": "lower", "category": "guardrail", "weight": 0.3, "threshold": 0.2},
            "sample_count": {"direction": "higher", "category": "data_quality", "weight": 0.0},
            "latency_ms": {"direction": "lower", "category": "system", "weight": 0.0},
        },
        "config": {"fast_window": 8, "slow_window": 21},
        "artifacts": [
            {"type": "json", "path": "runs/candidate.json", "metadata": {"node_id": "researcher"}},
            {"type": "log", "path": "runs/broker.log", "metadata": {"node_id": "broker"}},
        ],
        "metadata": {"data_source": "fixture_history"},
    }


class WorkflowContractNext20Test(unittest.TestCase):
    """Validate the next workflow-evidence expansion."""

    def test_contract_validator_rejects_missing_structure_and_warns_on_black_boxes(self) -> None:
        rejected = WorkflowContractValidator().validate({"workflow_id": "bad"})
        warning = WorkflowContractValidator().validate(_payload())

        self.assertEqual(rejected.status, "rejected")
        self.assertIn("run_id", {issue.field for issue in rejected.issues})
        self.assertEqual(warning.status, "warning")
        self.assertTrue(any(issue.code == "workflow.black_box_node" for issue in warning.issues))

    def test_ingest_builds_workflow_map_gap_report_and_node_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = EvidenceService(EvidenceStore(Path(tmp) / "evidence.db"))
            result = service.ingest_payload(_payload())
            workflow_map = service.workflow_map("quant_flow")
            gaps = service.gap_report("candidate")
            node_detail = service.node_detail("candidate", "researcher")
            black_box_detail = service.node_detail("candidate", "broker")

            self.assertEqual(result.run.scenario_id, "quant")
            self.assertEqual(workflow_map.workflow_id, "quant_flow")
            self.assertEqual(workflow_map.latest_run_id, "candidate")
            self.assertEqual(workflow_map.entry_node_ids, ["ingest"])
            self.assertEqual(workflow_map.exit_node_ids, ["broker", "report"])
            self.assertIn("broker", workflow_map.black_box_node_ids)
            self.assertIn("data_window", workflow_map.config_surfaces)
            self.assertEqual(gaps.status, "warning")
            self.assertIn("broker", gaps.black_box_node_ids)
            self.assertTrue(any(gap.code == "node.black_box" for gap in gaps.gaps))
            self.assertEqual(node_detail.node_id, "researcher")
            self.assertTrue(node_detail.optimizable)
            self.assertEqual(node_detail.metrics["sharpe"], 1.2)
            self.assertEqual(node_detail.input_summary, "bars + config")
            self.assertEqual(node_detail.artifact_refs[0]["path"], "runs/candidate.json")
            self.assertTrue(any(gap.code == "node.black_box" for gap in black_box_detail.gaps))
            self.assertEqual(black_box_detail.artifact_refs[0]["path"], "runs/broker.log")

    def test_goal_profile_boundary_trace_normalizer_and_decision_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "evidence.db"
            goal_store = OptimizationGoalStore(db_path)
            goal = goal_store.save(
                OptimizationGoalProfile(
                    scenario_id="quant",
                    primary_metrics=["sharpe"],
                    guardrail_metrics=["max_drawdown"],
                    max_cost_increase=0.1,
                    max_risk_level="approval",
                    preferences={"trading_frequency": "low"},
                )
            )
            loaded = goal_store.get("quant")
            assert loaded is not None

            allowed = CandidateBoundary().classify(CandidateChange(change_type="prompt_patch", magnitude=0.1))
            blocked = CandidateBoundary().classify(CandidateChange(change_type="auto_live_trade", magnitude=0.1))
            trace = TraceNormalizer().normalize(
                [
                    {"node": "researcher", "ok": True, "latency": 12, "output": "signal"},
                    {"step_id": "report", "status": "failed", "error": "missing chart"},
                ]
            )
            DecisionLogStore(db_path).record(
                DecisionRecord(
                    source_id="proposal-a",
                    source_type="proposal",
                    kind=DecisionKind.APPROVE,
                    scenario_id="quant",
                    actor="human",
                    action="approve",
                    comment="Small prompt patch improved sharpe.",
                    details={"proposal_kind": "prompt", "expected_metric": "sharpe"},
                )
            )
            memory = HumanDecisionMemory(db_path).summarize("quant")

            self.assertEqual(goal.scenario_id, "quant")
            self.assertEqual(loaded.primary_metrics, ["sharpe"])
            self.assertEqual(allowed.level, "allowed")
            self.assertEqual(blocked.level, "blocked")
            self.assertEqual(trace[0].node_id, "researcher")
            self.assertEqual(trace[1].status, "failed")
            self.assertEqual(memory.scenario_id, "quant")
            self.assertEqual(memory.approved_count, 1)
            self.assertIn("prompt", memory.approved_patterns)


if __name__ == "__main__":
    unittest.main()
