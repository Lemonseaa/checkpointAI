"""Tests for quant platform export adapters."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from loop_harness.harness import EvidenceHarness
from loop_harness.quant_data.platform_export import (
    JoinQuantBatchExportImporter,
    JoinQuantExportAdapter,
    QuantPlatformExport,
    evaluate_joinquant_export_quality,
)
from tests.quant_data.helpers import write_joinquant_export


def test_quant_platform_export_loads_required_files(tmp_path: Path) -> None:
    export_dir = tmp_path / "ma_5_20"
    write_joinquant_export(export_dir, run_id="jq_ma_5_20")

    export = QuantPlatformExport.load(export_dir)

    assert export.metadata.platform == "joinquant"
    assert export.metadata.run_id == "jq_ma_5_20"
    assert export.metrics["sharpe"] == 1.2
    assert len(export.equity_curve) >= 2
    assert export.equity_curve[0]["equity"] == "1.0"
    assert len(export.trades) == 1
    assert len(export.positions) == 1


def test_quant_platform_export_rejects_missing_required_files(tmp_path: Path) -> None:
    export_dir = tmp_path / "bad"
    export_dir.mkdir()
    (export_dir / "metadata.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required files"):
        QuantPlatformExport.load(export_dir)


def test_joinquant_export_adapter_converts_export_to_evidence_payload(tmp_path: Path) -> None:
    export_dir = tmp_path / "ma_5_20"
    write_joinquant_export(export_dir, run_id="jq_ma_5_20")

    payload = JoinQuantExportAdapter().to_payload(export_dir, workflow_id="joinquant_ma", scenario_id="quant_a_share")

    assert payload["run_id"] == "jq_ma_5_20"
    assert payload["run_kind"] == "historical"
    assert payload["metadata"]["platform"] == "joinquant"
    assert payload["metrics"]["sharpe"] == 1.2
    assert [node["id"] for node in payload["nodes"]] == [
        "load_joinquant_export",
        "parse_backtest_metrics",
        "parse_trades_positions",
        "evaluate_risk",
        "build_report",
    ]


def test_joinquant_quality_gate_blocks_incomplete_exports(tmp_path: Path) -> None:
    export_dir = tmp_path / "bad_quality"
    write_joinquant_export(export_dir, run_id="bad_quality")
    metadata = json.loads((export_dir / "metadata.json").read_text(encoding="utf-8"))
    metadata.pop("benchmark")
    metadata["parameters"] = {}
    (export_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    report = evaluate_joinquant_export_quality(QuantPlatformExport.load(export_dir))

    assert report.status == "blocked"
    assert "missing_benchmark" in report.blockers
    assert "missing_strategy_parameters" in report.blockers


def test_joinquant_batch_importer_compares_candidates_against_baseline(tmp_path: Path) -> None:
    batch_dir = tmp_path / "joinquant_exports"
    write_joinquant_export(batch_dir / "baseline", run_id="jq_baseline", total_return=0.1, sharpe=0.8)
    write_joinquant_export(batch_dir / "ma_5_20", run_id="jq_ma_5_20", total_return=0.18, sharpe=1.2)
    write_joinquant_export(batch_dir / "ma_10_60", run_id="jq_ma_10_60", total_return=0.12, sharpe=0.9)

    result = JoinQuantBatchExportImporter(EvidenceHarness(tmp_path / "jq.db")).import_batch(
        batch_dir,
        workflow_id="joinquant_batch",
        scenario_id="quant_a_share",
    )

    assert result.baseline_run_id == "jq_baseline"
    assert set(result.candidate_run_ids) == {"jq_ma_5_20", "jq_ma_10_60"}
    assert len(result.comparison_reports) == 2
    assert result.chart.best_candidate_run_id in result.candidate_run_ids
    assert "jq_ma_5_20" in result.markdown
