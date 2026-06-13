"""TradingAgents export-only spike tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from loop_harness.evidence.tradingagents import convert_tradingagents_export
from loop_harness.harness import EvidenceHarness

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "tradingagents_like_run.json"


class TradingAgentsSpikeTest(unittest.TestCase):
    """Validate TradingAgents-like export conversion without running TradingAgents."""

    def test_converter_maps_tradingagents_output_to_workflow_contract(self) -> None:
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))

        payload = convert_tradingagents_export(raw)

        self.assertEqual(payload["workflow_id"], "tradingagents_quant_research")
        self.assertEqual(payload["run_id"], "ta_candidate_001")
        self.assertEqual(payload["scenario_id"], "quant")
        self.assertEqual(payload["run_kind"], "fixture")
        self.assertEqual(payload["metadata"]["contract"], "quant_evidence_v1")
        self.assertEqual(len(payload["nodes"]), 4)
        self.assertEqual(len(payload["trace"]), 4)
        self.assertEqual(payload["config"]["fast_window"], 10)
        self.assertEqual(payload["metrics"]["sharpe"], 1.31)
        self.assertEqual(payload["metrics"]["max_drawdown"], 0.11)
        self.assertEqual(payload["metrics"]["sample_count"], 504.0)
        self.assertIn("max_drawdown", payload["metric_schema"])

    def test_converted_payload_ingests_and_generates_review_package(self) -> None:
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        baseline = convert_tradingagents_export(raw | {"run_id": "ta_baseline"})
        baseline["metrics"] = {
            **baseline["metrics"],
            "total_return": 0.16,
            "annual_return": 0.08,
            "excess_return": 0.0,
            "sharpe": 0.82,
            "max_drawdown": 0.15,
            "win_rate": 0.52,
        }
        candidate = convert_tradingagents_export(raw)

        with tempfile.TemporaryDirectory() as tmp:
            harness = EvidenceHarness(Path(tmp) / "evidence.db")
            harness.ingest_payload(baseline)
            harness.ingest_payload(candidate)
            report = harness.compare("ta_baseline", "ta_candidate_001")
            package = harness.review_package_for_runs("ta_baseline", ["ta_candidate_001"])

        self.assertEqual(report.recommendation.value, "inconclusive")
        self.assertEqual(package.recommended_action, "collect_more_evidence")
        self.assertIn("是否建议进入 paper trading：否", package.markdown)

    def test_fixture_evidence_is_rejected_by_quality_gate(self) -> None:
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        candidate = convert_tradingagents_export(raw)

        with tempfile.TemporaryDirectory() as tmp:
            harness = EvidenceHarness(Path(tmp) / "evidence.db")
            result = harness.ingest_payload(candidate)

        quality = result.report.evidence["quality"]
        self.assertEqual(quality["status"], "rejected")
        self.assertIn("fixture_not_real_evidence", quality["reasons"])

    def test_converter_rejects_missing_core_metrics(self) -> None:
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        raw["metrics"].pop("max_drawdown")

        with self.assertRaisesRegex(ValueError, "max_drawdown"):
            convert_tradingagents_export(raw)

    def test_spike_script_writes_contract_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "payload.json"
            command = [
                sys.executable,
                "scripts/business_lines/quant/convert_tradingagents_export.py",
                "--input",
                str(FIXTURE),
                "--output",
                str(output),
            ]

            completed = subprocess.run(command, cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True)
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("converted_tradingagents_export", completed.stdout)
        self.assertEqual(payload["metadata"]["source"], "tradingagents_spike")


if __name__ == "__main__":
    unittest.main()
