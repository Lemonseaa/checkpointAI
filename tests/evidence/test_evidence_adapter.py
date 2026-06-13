"""Tests for the external workflow evidence adapter."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from loop_harness.evidence import EvidenceService, EvidenceStore
from loop_harness.evidence.models import DecisionRecommendation


def _run_payload(run_id: str, sharpe: float, drawdown: float) -> dict[str, object]:
    return {
        "workflow_id": "quant_backtest_v1",
        "run_id": run_id,
        "run_kind": "historical",
        "nodes": [
            {"id": "load_data", "name": "Load Data", "type": "data"},
            {"id": "strategy", "name": "Strategy", "type": "agent"},
            {"id": "broker", "name": "Broker API", "type": "external"},
            {"id": "report", "name": "Report", "type": "output"},
        ],
        "edges": [
            {"source": "load_data", "target": "strategy"},
            {"source": "strategy", "target": "broker"},
            {"source": "strategy", "target": "report"},
        ],
        "trace": [
            {"node_id": "load_data", "status": "succeeded", "duration_ms": 120, "metrics": {"sample_count": 120}},
            {"node_id": "strategy", "status": "succeeded", "duration_ms": 340, "metrics": {"sharpe": sharpe}},
            {"node_id": "report", "status": "succeeded", "duration_ms": 80},
        ],
        "metrics": {
            "total_return": 0.18 + sharpe / 100,
            "sharpe": sharpe,
            "max_drawdown": drawdown,
            "sample_count": 120,
            "latency_ms": 540,
        },
        "metric_schema": {
            "total_return": {"direction": "higher", "category": "business", "weight": 0.25},
            "sharpe": {"direction": "higher", "category": "business", "weight": 0.45},
            "max_drawdown": {
                "direction": "lower",
                "category": "guardrail",
                "weight": 0.3,
                "threshold": 0.25,
                "is_guardrail": True,
            },
            "sample_count": {"direction": "higher", "category": "data_quality", "weight": 0.0},
            "latency_ms": {"direction": "lower", "category": "system", "weight": 0.0},
        },
        "config": {"strategy": "moving_average", "fast_window": 8},
        "artifacts": [{"type": "csv", "path": "results.csv"}],
        "metadata": {"data_source": "vendor_historical_prices"},
    }


class EvidenceAdapterTest(unittest.TestCase):
    """Validate R1 evidence ingest, visualization, comparison, and reports."""

    def test_ingest_generates_visualization_and_marks_black_box_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = EvidenceService(EvidenceStore(Path(tmp) / "evidence.db"))

            result = service.ingest_payload(_run_payload("run_a", sharpe=1.2, drawdown=0.12))

            self.assertEqual(result.run.run_id, "run_a")
            self.assertEqual(result.visualization.total_nodes, 4)
            self.assertAlmostEqual(result.visualization.trace_coverage, 0.75)
            self.assertAlmostEqual(result.visualization.metric_coverage, 0.5)
            self.assertEqual(result.visualization.black_box_node_ids, ["broker"])
            self.assertIn("broker", result.report.black_box_node_ids)
            self.assertEqual(result.report.recommendation, DecisionRecommendation.CONTINUE_SHADOW)

    def test_compare_uses_metric_schema_and_generates_decision_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = EvidenceService(EvidenceStore(Path(tmp) / "evidence.db"))
            service.ingest_payload(_run_payload("baseline", sharpe=0.9, drawdown=0.14))
            service.ingest_payload(_run_payload("candidate", sharpe=1.4, drawdown=0.10))

            report = service.compare("baseline", "candidate")
            stored_report = service.store.get_comparison_report("baseline", "candidate")

            self.assertEqual(report.baseline_run_id, "baseline")
            self.assertEqual(report.candidate_run_id, "candidate")
            self.assertIsNotNone(stored_report)
            assert stored_report is not None
            self.assertEqual(stored_report.candidate_run_id, "candidate")
            self.assertTrue(report.comparison)
            assert report.comparison is not None
            self.assertTrue(report.comparison.improved)
            self.assertGreater(report.comparison.objective_score, 0)
            self.assertEqual(report.recommendation, DecisionRecommendation.APPROVE)
            self.assertIn("sharpe", report.comparison.business_metric_diffs)
            self.assertIn("latency_ms", report.comparison.system_metric_diffs)

    def test_ingest_file_round_trips_through_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            payload_path = tmp_path / "run.json"
            payload_path.write_text(json.dumps(_run_payload("stored", 1.1, 0.11)), encoding="utf-8")
            store = EvidenceStore(tmp_path / "evidence.db")
            service = EvidenceService(store)

            service.ingest_file(payload_path)
            stored = store.get_run("stored")

            self.assertIsNotNone(stored)
            assert stored is not None
            self.assertEqual(stored.run.workflow_id, "quant_backtest_v1")
            self.assertEqual(stored.report.run_id, "stored")


if __name__ == "__main__":
    unittest.main()
