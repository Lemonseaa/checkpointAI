"""Tests for A-share real-sample manifests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from loop_harness.quant_data.manifest import AShareSampleManifest


def _write_sample_csv(path: Path, ts_code: str) -> None:
    path.write_text(
        "ts_code,trade_date,open,high,low,close,vol,amount\n"
        f"{ts_code},20240102,100,105,99,104,1000,100000\n"
        f"{ts_code},20240103,104,108,103,107,1200,120000\n",
        encoding="utf-8",
    )


def test_manifest_loads_entries_and_resolves_relative_paths(tmp_path: Path) -> None:
    daily_dir = tmp_path / "daily"
    daily_dir.mkdir()
    csv_path = daily_dir / "600519.SH.csv"
    _write_sample_csv(csv_path, "600519.SH")
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
                        "end_date": "2024-01-31",
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

    manifest = AShareSampleManifest.load(manifest_path)

    assert len(manifest.entries) == 1
    entry = manifest.entries[0]
    assert entry.ts_code == "600519.SH"
    assert entry.resolved_path == csv_path
    assert entry.source_vendor == "tushare_pro_export"
    assert entry.decision_grade is True


def test_manifest_rejects_missing_required_fields(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"entries": [{"ts_code": "600519.SH"}]}), encoding="utf-8")

    with pytest.raises(ValueError, match="Manifest entry"):
        AShareSampleManifest.load(manifest_path)
