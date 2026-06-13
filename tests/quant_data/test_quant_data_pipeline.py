"""Tests for converting A-share backtests into evidence runs."""

from __future__ import annotations

from datetime import date

from loop_harness.harness import EvidenceHarness
from loop_harness.quant_data.pipeline import AShareQuantLoopPipeline
from loop_harness.quant_data.providers import AShareStaticProvider


def test_a_share_quant_pipeline_ingests_baseline_candidate_and_chart(tmp_path) -> None:  # type: ignore[no-untyped-def]
    harness = EvidenceHarness(tmp_path / "quant.db")
    dataset = AShareStaticProvider().fetch(
        ts_code="600519.SH",
        start=date(2024, 1, 1),
        end=date(2024, 12, 31),
        adjusted_mode="qfq",
    )

    result = AShareQuantLoopPipeline(harness).run(
        dataset,
        workflow_id="a_share_quant_600519",
        scenario_id="quant_a_share",
        run_kind="historical",
        fast_window=5,
        slow_window=20,
    )

    assert result.baseline_run_id == "a_share_quant_600519_baseline"
    assert result.candidate_run_id == "a_share_quant_600519_ma_5_20"
    assert result.data_quality.status == "warning"
    assert "not_decision_grade" in result.data_quality.flags
    assert result.comparison.candidate_run_id == result.candidate_run_id
    assert result.chart.baseline_run_id == result.baseline_run_id
    assert result.chart.candidate_points
    stored = harness.store.get_run(result.candidate_run_id)
    assert stored is not None
    assert stored.run.run_kind.value == "fixture"
    assert stored.run.metadata["market"] == "A_SHARE"
    assert stored.run.metadata["data_quality"]["decision_grade"] is False
