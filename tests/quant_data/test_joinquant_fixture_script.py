"""Tests for JoinQuant fixture generation script."""

from __future__ import annotations

from pathlib import Path

from loop_harness.harness import EvidenceHarness
from loop_harness.quant_data.platform_export import JoinQuantRealDrillRunner, QuantPlatformExport
from scripts.business_lines.quant.create_joinquant_fixture import create_joinquant_fixture


def test_create_joinquant_fixture_outputs_drill_compatible_batch(tmp_path: Path) -> None:
    output_dir = tmp_path / "joinquant_fixture"

    created = create_joinquant_fixture(output_dir)

    assert created == output_dir
    assert QuantPlatformExport.load(output_dir / "baseline").metadata.run_id == "jq_fixture_baseline"
    assert QuantPlatformExport.load(output_dir / "ma_5_20").metrics["sharpe"] == 1.2
    assert QuantPlatformExport.load(output_dir / "ma_10_60").metrics["max_drawdown"] == 0.16

    summary = JoinQuantRealDrillRunner(EvidenceHarness(tmp_path / "fixture_drill.db")).run(
        output_dir,
        workflow_id="jq_fixture_drill",
        scenario_id="quant_a_share",
        normalize_dir=tmp_path / "normalized_fixture",
    )

    assert summary.ready_count == 3
    assert summary.batch_result is not None
    assert summary.batch_result.candidate_run_ids == ["jq_fixture_ma_10_60", "jq_fixture_ma_5_20"]
