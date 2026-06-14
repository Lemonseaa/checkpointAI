"""Tests for quant platform export adapters."""

from __future__ import annotations

import csv
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


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_joinquant_export(
    path: Path,
    *,
    run_id: str,
    strategy_name: str = "ma_cross",
    sharpe: float = 1.2,
    max_drawdown: float = 0.12,
    total_return: float = 0.18,
) -> None:
    path.mkdir(parents=True)
    (path / "metadata.json").write_text(
        json.dumps(
            {
                "platform": "joinquant",
                "run_id": run_id,
                "strategy_name": strategy_name,
                "strategy_version": "v1",
                "universe": ["600519.XSHG"],
                "benchmark": "000300.XSHG",
                "start_date": "2020-01-01",
                "end_date": "2024-12-31",
                "initial_cash": 1000000,
                "commission": 0.0003,
                "slippage": 0.001,
                "frequency": "daily",
                "run_kind": "historical",
                "parameters": {"fast_window": 5, "slow_window": 20},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (path / "metrics.json").write_text(
        json.dumps(
            {
                "total_return": total_return,
                "annual_return": 0.08,
                "sharpe": sharpe,
                "max_drawdown": max_drawdown,
                "volatility": 0.16,
                "win_rate": 0.54,
                "turnover": 0.8,
                "trade_count": 24,
                "benchmark_return": 0.1,
                "excess_return": total_return - 0.1,
                "sample_count": 1000,
            }
        ),
        encoding="utf-8",
    )
    _write_csv(
        path / "equity_curve.csv",
        ["date", "equity"],
        [{"date": "2020-01-01", "equity": 1.0}, {"date": "2024-12-31", "equity": 1.18}],
    )
    _write_csv(
        path / "trades.csv",
        ["datetime", "symbol", "side", "price", "amount", "value"],
        [{"datetime": "2020-01-02", "symbol": "600519.XSHG", "side": "buy", "price": 100, "amount": 100, "value": 10000}],
    )
    _write_csv(
        path / "positions.csv",
        ["date", "symbol", "amount", "value"],
        [{"date": "2020-01-02", "symbol": "600519.XSHG", "amount": 100, "value": 10000}],
    )
    (path / "logs.txt").write_text("JoinQuant backtest completed\n", encoding="utf-8")


def test_quant_platform_export_loads_required_files(tmp_path: Path) -> None:
    export_dir = tmp_path / "ma_5_20"
    _write_joinquant_export(export_dir, run_id="jq_ma_5_20")

    export = QuantPlatformExport.load(export_dir)

    assert export.metadata.platform == "joinquant"
    assert export.metadata.run_id == "jq_ma_5_20"
    assert export.metrics["sharpe"] == 1.2
    assert len(export.equity_curve) == 2
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
    _write_joinquant_export(export_dir, run_id="jq_ma_5_20")

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
    _write_joinquant_export(export_dir, run_id="bad_quality")
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
    _write_joinquant_export(batch_dir / "baseline", run_id="jq_baseline", total_return=0.1, sharpe=0.8)
    _write_joinquant_export(batch_dir / "ma_5_20", run_id="jq_ma_5_20", total_return=0.18, sharpe=1.2)
    _write_joinquant_export(batch_dir / "ma_10_60", run_id="jq_ma_10_60", total_return=0.12, sharpe=0.9)

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
