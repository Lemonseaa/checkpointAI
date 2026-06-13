"""CLI tests for A-share quant loop commands."""

from __future__ import annotations

import json

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
