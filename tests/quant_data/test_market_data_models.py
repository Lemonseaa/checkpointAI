"""Tests for normalized A-share market data contracts."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from loop_harness.quant_data.models import AShareMarketBar, AShareMarketDataSet


def _bar(day: int, close: float = 100.0) -> AShareMarketBar:
    return AShareMarketBar(
        trade_date=date(2024, 1, 1) + timedelta(days=day - 1),
        open=close - 1,
        high=close + 1,
        low=close - 2,
        close=close,
        volume=1000.0,
    )


def test_a_share_market_data_set_reports_valid_daily_data() -> None:
    bars = [_bar(day, close=100.0 + day) for day in range(1, 41)]

    dataset = AShareMarketDataSet(
        ts_code="600519.SH",
        name="贵州茅台",
        frequency="1d",
        source="vendor_csv",
        vendor="tushare_pro_export",
        license_note="operator-provided licensed export",
        adjusted_mode="qfq",
        decision_grade=True,
        bars=bars,
    )

    report = dataset.quality_report(min_bars=30)

    assert report.status == "valid"
    assert report.sample_count == 40
    assert report.flags == []
    assert dataset.start_date == date(2024, 1, 1)
    assert dataset.end_date == date(2024, 2, 9)


def test_a_share_market_data_set_flags_too_few_and_unadjusted_data() -> None:
    dataset = AShareMarketDataSet(
        ts_code="000001.SZ",
        name="平安银行",
        frequency="1d",
        source="static_a_share",
        vendor="fixture",
        license_note="test fixture",
        adjusted_mode="none",
        decision_grade=False,
        bars=[_bar(1), _bar(2)],
    )

    report = dataset.quality_report(min_bars=30)

    assert report.status == "warning"
    assert "sample_count_below_minimum" in report.flags
    assert "unadjusted_prices" in report.flags
    assert "not_decision_grade" in report.flags


def test_a_share_market_data_set_rejects_non_chronological_bars() -> None:
    with pytest.raises(ValueError, match="chronological"):
        AShareMarketDataSet(
            ts_code="600519.SH",
            name="贵州茅台",
            frequency="1d",
            source="vendor_csv",
            vendor="tushare_pro_export",
            license_note="test fixture",
            adjusted_mode="qfq",
            decision_grade=True,
            bars=[
                AShareMarketBar(
                    trade_date=date(2024, 1, 2),
                    open=100,
                    high=101,
                    low=99,
                    close=100,
                    volume=1,
                ),
                AShareMarketBar(
                    trade_date=date(2024, 1, 1),
                    open=100,
                    high=101,
                    low=99,
                    close=100,
                    volume=1,
                ),
            ],
        )


def test_market_bar_rejects_invalid_price_range() -> None:
    with pytest.raises(ValueError, match="high must be"):
        AShareMarketBar(
            trade_date=date(2024, 1, 1),
            open=100,
            high=95,
            low=90,
            close=100,
            volume=1000,
        )
