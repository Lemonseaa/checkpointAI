"""TradingAgents real-sample compatibility scoring tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from loop_harness.evidence.tradingagents import convert_tradingagents_export
from loop_harness.evidence.tradingagents_compatibility import score_tradingagents_samples

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "tradingagents_like_run.json"


class TradingAgentsCompatibilityTest(unittest.TestCase):
    """Score real samples before building a TradingAgents execution adapter."""

    def test_fixture_only_samples_are_no_go(self) -> None:
        payload = convert_tradingagents_export(json.loads(FIXTURE.read_text(encoding="utf-8")))

        report = score_tradingagents_samples([payload])

        self.assertEqual(report.decision, "no_go")
        self.assertIn("fixture_only", report.blockers)
        self.assertLess(report.overall_score, 0.5)

    def test_real_but_underpowered_samples_need_more_samples(self) -> None:
        payload = _historical_payload("hist_1")

        report = score_tradingagents_samples([payload])

        self.assertEqual(report.decision, "needs_more_samples")
        self.assertIn("sample_count_below_minimum", report.blockers)

    def test_missing_mapping_fields_need_mapping_fix(self) -> None:
        payload = _historical_payload("hist_1")
        payload["trace"] = []
        payload["config"] = {}

        report = score_tradingagents_samples([payload] * 5)

        self.assertEqual(report.decision, "needs_mapping_fix")
        self.assertIn("missing_trace", report.blockers)
        self.assertIn("missing_config_surface", report.blockers)

    def test_enough_real_samples_with_structure_are_go(self) -> None:
        payloads = [_historical_payload(f"hist_{index}") for index in range(1, 6)]

        report = score_tradingagents_samples(payloads)

        self.assertEqual(report.decision, "go")
        self.assertGreaterEqual(report.overall_score, 0.8)
        self.assertEqual(report.real_sample_count, 5)
        self.assertEqual(report.scores["business_metrics"], 1.0)


def _historical_payload(run_id: str) -> dict[str, object]:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["run_id"] = run_id
    raw["run_kind"] = "historical"
    raw["metadata"] = {"data_source": "vendor_historical_prices"}
    payload = convert_tradingagents_export(raw)
    payload["metadata"] = {**payload["metadata"], "data_source": "vendor_historical_prices"}
    return payload


if __name__ == "__main__":
    unittest.main()
