"""Evidence quality gate tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from loop_harness.evidence import EvidenceService, EvidenceStore


class EvidenceQualityTest(unittest.TestCase):
    """Evidence reports should explain whether evidence is trustworthy."""

    def test_historical_full_coverage_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = EvidenceService(EvidenceStore(Path(tmp) / "quality.db")).ingest_payload(
                _payload(
                    run_id="historical-ok",
                    run_kind="historical",
                    sample_count=200,
                    trace_all=True,
                    black_box=False,
                )
            )

        quality = result.report.evidence["quality"]
        self.assertEqual(quality["status"], "accepted")
        self.assertGreaterEqual(quality["score"], 0.8)
        self.assertEqual(quality["reasons"], [])

    def test_black_box_run_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = EvidenceService(EvidenceStore(Path(tmp) / "quality.db")).ingest_payload(
                _payload(
                    run_id="black-box",
                    run_kind="historical",
                    sample_count=200,
                    trace_all=True,
                    black_box=True,
                )
            )

        quality = result.report.evidence["quality"]
        self.assertEqual(quality["status"], "warning")
        self.assertIn("black_box_nodes_present", quality["reasons"])

    def test_low_sample_synthetic_run_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = EvidenceService(EvidenceStore(Path(tmp) / "quality.db")).ingest_payload(
                _payload(
                    run_id="synthetic-low",
                    run_kind="synthetic",
                    sample_count=5,
                    trace_all=False,
                    black_box=False,
                )
            )

        quality = result.report.evidence["quality"]
        self.assertEqual(quality["status"], "rejected")
        self.assertIn("synthetic_low_sample", quality["reasons"])
        self.assertIn("low_trace_coverage", quality["reasons"])

    def test_historical_run_with_fixture_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = _payload(
                run_id="fixture-source",
                run_kind="historical",
                sample_count=200,
                trace_all=True,
                black_box=False,
            )
            payload["metadata"] = {"data_source": "fixture_history"}
            result = EvidenceService(EvidenceStore(Path(tmp) / "quality.db")).ingest_payload(payload)

        quality = result.report.evidence["quality"]
        self.assertEqual(quality["status"], "rejected")
        self.assertIn("non_decision_data_source", quality["reasons"])


def _payload(
    *,
    run_id: str,
    run_kind: str,
    sample_count: int,
    trace_all: bool,
    black_box: bool,
) -> dict[str, object]:
    trace = [
        {"node_id": "load", "status": "succeeded", "metrics": {"sample_count": sample_count}},
        {"node_id": "strategy", "status": "succeeded", "metrics": {"sharpe": 1.1}},
    ]
    if trace_all:
        trace.append({"node_id": "risk", "status": "succeeded", "metrics": {"max_drawdown": 0.12}})
    return {
        "workflow_id": "quality_workflow",
        "run_id": run_id,
        "run_kind": run_kind,
        "nodes": [
            {"id": "load", "type": "tool"},
            {"id": "strategy", "type": "agent"},
            {"id": "risk", "type": "tool", "metadata": {"black_box": black_box}},
        ],
        "edges": [
            {"source": "load", "target": "strategy"},
            {"source": "strategy", "target": "risk"},
        ],
        "trace": trace,
        "metrics": {
            "sharpe": 1.1,
            "max_drawdown": 0.12,
            "sample_count": sample_count,
            "latency_ms": 300,
        },
        "metric_schema": {
            "sharpe": {"direction": "higher", "category": "business", "weight": 0.7},
            "max_drawdown": {"direction": "lower", "category": "business", "weight": 0.3},
            "sample_count": {"direction": "higher", "category": "data_quality", "weight": 0.0},
            "latency_ms": {"direction": "lower", "category": "system", "weight": 0.0},
        },
    }


if __name__ == "__main__":
    unittest.main()
