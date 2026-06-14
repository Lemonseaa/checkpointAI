"""CLI tests for A-share quant loop commands."""

from __future__ import annotations

import json
from pathlib import Path

from loop_harness.cli import main
from loop_harness.harness import EvidenceHarness
from tests.quant_data.helpers import write_joinquant_alias_export, write_joinquant_export


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


def test_joinquant_import_cli_ingests_single_export(tmp_path: Path, capsys) -> None:
    export_dir = tmp_path / "joinquant" / "ma_5_20"
    write_joinquant_export(export_dir, run_id="jq_ma_5_20")

    exit_code = main(
        [
            "--db",
            str(tmp_path / "jq.db"),
            "evidence",
            "joinquant-import",
            "--export-dir",
            str(export_dir),
            "--workflow",
            "joinquant_ma",
            "--scenario",
            "quant_a_share",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["run_id"] == "jq_ma_5_20"
    assert payload["recommendation"] in {"approve", "continue_shadow", "inconclusive", "reject"}
    assert payload["quality"]["status"] == "valid"


def test_joinquant_validate_cli_reports_quality_without_ingesting(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "jq_validate.db"
    export_dir = tmp_path / "joinquant" / "ma_5_20"
    write_joinquant_export(export_dir, run_id="jq_ma_5_20")

    exit_code = main(
        [
            "--db",
            str(db_path),
            "evidence",
            "joinquant-validate",
            "--export-dir",
            str(export_dir),
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["run_id"] == "jq_ma_5_20"
    assert payload["quality"]["status"] == "valid"
    assert EvidenceHarness(db_path).list_runs() == []


def test_joinquant_diagnose_cli_reports_alias_mappings(tmp_path: Path, capsys) -> None:
    export_dir = tmp_path / "joinquant" / "alias"
    write_joinquant_alias_export(export_dir, run_id="jq_alias")

    exit_code = main(
        [
            "--db",
            str(tmp_path / "jq_diag.db"),
            "evidence",
            "joinquant-diagnose",
            "--export-dir",
            str(export_dir),
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["run_id"] == "jq_alias"
    assert payload["ready_to_import"] is True
    assert payload["field_mappings"]["equity_curve.csv"]["portfolio_value"] == "equity"


def test_joinquant_normalize_cli_writes_standard_copy(tmp_path: Path, capsys) -> None:
    export_dir = tmp_path / "joinquant" / "alias"
    output_dir = tmp_path / "joinquant" / "normalized"
    write_joinquant_alias_export(export_dir, run_id="jq_alias")

    exit_code = main(
        [
            "--db",
            str(tmp_path / "jq_norm.db"),
            "evidence",
            "joinquant-normalize",
            "--export-dir",
            str(export_dir),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ready_to_import"] is True
    assert (output_dir / "equity_curve.csv").read_text(encoding="utf-8").splitlines()[0] == "date,equity"


def test_joinquant_batch_cli_outputs_review_payload(tmp_path: Path, capsys) -> None:
    batch_dir = tmp_path / "joinquant_exports"
    write_joinquant_export(batch_dir / "baseline", run_id="jq_baseline", total_return=0.1, sharpe=0.8)
    write_joinquant_export(batch_dir / "ma_5_20", run_id="jq_ma_5_20", total_return=0.18, sharpe=1.2)

    exit_code = main(
        [
            "--db",
            str(tmp_path / "jq_batch.db"),
            "evidence",
            "joinquant-batch",
            "--batch-dir",
            str(batch_dir),
            "--workflow",
            "joinquant_batch",
            "--scenario",
            "quant_a_share",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["baseline_run_id"] == "jq_baseline"
    assert payload["candidate_run_ids"] == ["jq_ma_5_20"]
    assert payload["chart"]["best_candidate_run_id"] == "jq_ma_5_20"
    assert "paper_trading_discussion" in payload
    assert payload["import_readiness_summary"]["ready_count"] == 2
    assert payload["curve_payload"]["equity_curves"]


def test_joinquant_batch_cli_preflight_blocks_partial_import(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "jq_bad_batch.db"
    batch_dir = tmp_path / "joinquant_exports"
    write_joinquant_export(batch_dir / "baseline", run_id="jq_baseline", total_return=0.1, sharpe=0.8)
    bad_candidate = batch_dir / "ma_bad"
    write_joinquant_export(bad_candidate, run_id="jq_bad", total_return=0.2, sharpe=1.3)
    (bad_candidate / "trades.csv").unlink()

    exit_code = main(
        [
            "--db",
            str(db_path),
            "evidence",
            "joinquant-batch",
            "--batch-dir",
            str(batch_dir),
            "--workflow",
            "joinquant_batch",
            "--scenario",
            "quant_a_share",
        ]
    )

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "preflight failed" in output
    assert "ma_bad" in output
    assert EvidenceHarness(db_path).list_runs(workflow_id="joinquant_batch") == []
