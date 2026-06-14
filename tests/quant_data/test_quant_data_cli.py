"""CLI tests for A-share quant loop commands."""

from __future__ import annotations

import json
from pathlib import Path

from loop_harness.cli import main


def test_quant_a_share_loop_demo_cli_outputs_evidence_ids(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "quant_cli.db"

    exit_code = main(
        [
            "--db",
            str(db_path),
            "evidence",
            "quant-a-share-loop",
            "--symbol",
            "600519.SH",
            "--provider",
            "static-a-share",
            "--start",
            "2024-01-01",
            "--end",
            "2024-12-31",
            "--fast-window",
            "5",
            "--slow-window",
            "20",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["baseline_run_id"] == "a_share_quant_600519_SH_baseline"
    assert payload["candidate_run_id"] == "a_share_quant_600519_SH_ma_5_20"
    assert payload["data_quality"]["status"] == "warning"
    assert "not_decision_grade" in payload["data_quality"]["flags"]
    assert payload["recommendation"] == "inconclusive"


def test_quant_a_share_batch_cli_runs_manifest_grid(tmp_path: Path, capsys) -> None:
    daily = tmp_path / "daily"
    daily.mkdir()
    csv_path = daily / "600519.SH.csv"
    rows = ["ts_code,trade_date,open,high,low,close,vol,amount"]
    for index in range(130):
        close = 100 + index * 0.2
        rows.append(
            f"600519.SH,2024{((index) // 28) + 1:02d}{((index) % 28) + 1:02d},"
            f"{close - 1:.2f},{close + 1:.2f},{close - 2:.2f},{close:.2f},1000,100000"
        )
    csv_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
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
                        "end_date": "2024-05-18",
                        "decision_grade": True,
                        "license_note": "operator-provided licensed export",
                        "file_path": "daily/600519.SH.csv",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--db",
            str(tmp_path / "batch.db"),
            "evidence",
            "quant-a-share-batch",
            "--manifest",
            str(manifest_path),
            "--fast-windows",
            "5,10",
            "--slow-windows",
            "20",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["symbol_count"] == 1
    assert payload["run_count"] == 2
    assert payload["chart_payload"]["parameter_heatmap"]
    assert "贵州茅台" in payload["markdown"]
