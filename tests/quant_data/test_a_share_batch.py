"""Tests for A-share batch quant loop execution."""

from __future__ import annotations

import json
from pathlib import Path

from loop_harness.harness import EvidenceHarness
from loop_harness.quant_data.batch import (
    AShareBatchQuantRunner,
    AShareParameterGrid,
    summarize_manifest_quality,
)
from loop_harness.quant_data.manifest import AShareSampleManifest


def _write_csv(path: Path, ts_code: str, *, days: int = 140) -> None:
    rows = ["ts_code,trade_date,open,high,low,close,vol,amount"]
    for index in range(days):
        day = index + 1
        close = 100 + index * 0.2
        rows.append(
            f"{ts_code},2024{((day - 1) // 28) + 1:02d}{((day - 1) % 28) + 1:02d},"
            f"{close - 1:.2f},{close + 1:.2f},{close - 2:.2f},{close:.2f},1000,100000"
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _manifest(tmp_path: Path) -> AShareSampleManifest:
    daily = tmp_path / "daily"
    daily.mkdir()
    _write_csv(daily / "600519.SH.csv", "600519.SH")
    _write_csv(daily / "000001.SZ.csv", "000001.SZ")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "ts_code": "600519.SH",
                        "name": "贵州茅台",
                        "source_vendor": "tushare_pro_export",
                        "adjusted_mode": "qfq",
                        "start_date": "2024-01-01",
                        "end_date": "2024-05-28",
                        "decision_grade": True,
                        "license_note": "operator-provided licensed export",
                        "file_path": "daily/600519.SH.csv",
                    },
                    {
                        "ts_code": "000001.SZ",
                        "name": "平安银行",
                        "source_vendor": "tushare_pro_export",
                        "adjusted_mode": "qfq",
                        "start_date": "2024-01-01",
                        "end_date": "2024-05-28",
                        "decision_grade": True,
                        "license_note": "operator-provided licensed export",
                        "file_path": "daily/000001.SZ.csv",
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return AShareSampleManifest.load(manifest_path)


def test_summarize_manifest_quality_reads_vendor_csv_files(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)

    summary = summarize_manifest_quality(manifest, min_bars=120)

    assert summary.total_symbols == 2
    assert summary.decision_grade_symbols == 2
    assert summary.non_decision_grade_symbols == 0
    assert summary.by_symbol["600519.SH"].sample_count == 140
    assert summary.by_symbol["600519.SH"].flags == []


def test_parameter_grid_generates_only_valid_pairs() -> None:
    grid = AShareParameterGrid(fast_windows=[5, 20], slow_windows=[10, 20])

    assert grid.pairs() == [(5, 10), (5, 20)]


def test_batch_runner_runs_manifest_entries_and_parameter_grid(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    harness = EvidenceHarness(tmp_path / "batch.db")

    result = AShareBatchQuantRunner(harness).run_grid(
        manifest,
        grid=AShareParameterGrid(fast_windows=[5], slow_windows=[20, 60]),
        scenario_id="quant_a_share",
        run_kind="historical",
    )

    assert result.symbol_count == 2
    assert result.run_count == 4
    assert result.best_candidates
    assert set(result.quality_summary.by_symbol) == {"600519.SH", "000001.SZ"}
    assert result.recommendation_distribution
    assert "600519.SH" in result.markdown
    assert result.chart_payload["symbol_ranking"]
    assert result.chart_payload["parameter_heatmap"]
