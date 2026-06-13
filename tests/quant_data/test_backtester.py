"""Tests for the A-share baseline backtester."""

from __future__ import annotations

from datetime import date

from loop_harness.quant_data.backtest import AShareBacktester
from loop_harness.quant_data.providers import AShareStaticProvider


def test_buy_and_hold_backtest_returns_quant_metrics() -> None:
    dataset = AShareStaticProvider().fetch(
        ts_code="600519.SH",
        start=date(2024, 1, 1),
        end=date(2024, 8, 31),
        adjusted_mode="qfq",
    )

    result = AShareBacktester().buy_and_hold(dataset, run_id="baseline")

    assert result.run_id == "baseline"
    assert result.strategy == "buy_and_hold"
    assert result.metrics.sample_count == len(dataset.bars)
    assert result.metrics.trade_count == 1
    assert result.metrics.max_drawdown >= 0
    assert 0 <= result.metrics.win_rate <= 1


def test_moving_average_crossover_returns_strategy_parameters() -> None:
    dataset = AShareStaticProvider().fetch(
        ts_code="600519.SH",
        start=date(2024, 1, 1),
        end=date(2024, 12, 31),
        adjusted_mode="qfq",
    )

    result = AShareBacktester().moving_average_crossover(
        dataset,
        run_id="candidate",
        fast_window=5,
        slow_window=20,
    )

    assert result.strategy == "moving_average_crossover"
    assert result.parameters == {"fast_window": 5, "slow_window": 20}
    assert result.metrics.sample_count == len(dataset.bars)
    assert result.metrics.trade_count >= 0


def test_moving_average_crossover_rejects_invalid_windows() -> None:
    dataset = AShareStaticProvider().fetch(
        ts_code="600519.SH",
        start=date(2024, 1, 1),
        end=date(2024, 12, 31),
        adjusted_mode="qfq",
    )

    try:
        AShareBacktester().moving_average_crossover(
            dataset,
            run_id="bad",
            fast_window=20,
            slow_window=5,
        )
    except ValueError as exc:
        assert "fast_window must be smaller" in str(exc)
    else:
        raise AssertionError("invalid windows should be rejected")
