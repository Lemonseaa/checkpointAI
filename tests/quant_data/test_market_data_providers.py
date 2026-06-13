"""Tests for A-share market data providers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from loop_harness.quant_data.providers import (
    AShareStaticProvider,
    TushareDailyProvider,
    VendorCSVAShareProvider,
)


def test_static_a_share_provider_returns_decision_grade_false_fixture() -> None:
    provider = AShareStaticProvider()

    dataset = provider.fetch(
        ts_code="600519.SH",
        start=date(2024, 1, 1),
        end=date(2024, 8, 31),
        adjusted_mode="qfq",
    )

    assert dataset.ts_code == "600519.SH"
    assert dataset.source == "static_a_share"
    assert dataset.vendor == "fixture"
    assert dataset.decision_grade is False
    assert len(dataset.bars) >= 120
    assert dataset.quality_report(min_bars=120).flags == ["not_decision_grade"]


def test_vendor_csv_provider_loads_tushare_style_daily_export(tmp_path: Path) -> None:
    csv_path = tmp_path / "600519_daily.csv"
    csv_path.write_text(
        "ts_code,trade_date,open,high,low,close,vol,amount\n"
        "600519.SH,20240102,100,105,99,104,1000,100000\n"
        "600519.SH,20240103,104,108,103,107,1200,120000\n",
        encoding="utf-8",
    )
    provider = VendorCSVAShareProvider(csv_path, vendor="tushare_pro_export")

    dataset = provider.fetch(
        ts_code="600519.SH",
        start=date(2024, 1, 1),
        end=date(2024, 1, 31),
        adjusted_mode="qfq",
    )

    assert dataset.source == "vendor_csv"
    assert dataset.vendor == "tushare_pro_export"
    assert dataset.decision_grade is True
    assert dataset.bars[0].trade_date == date(2024, 1, 2)
    assert dataset.bars[1].close == 107


def test_vendor_csv_provider_rejects_missing_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("ts_code,trade_date,open\n600519.SH,20240102,100\n", encoding="utf-8")
    provider = VendorCSVAShareProvider(csv_path, vendor="tushare_pro_export")

    with pytest.raises(ValueError, match="missing required columns"):
        provider.fetch(
            ts_code="600519.SH",
            start=date(2024, 1, 1),
            end=date(2024, 1, 31),
            adjusted_mode="qfq",
        )


def test_tushare_provider_requires_explicit_token() -> None:
    with pytest.raises(ValueError, match="token"):
        TushareDailyProvider(token="")
