"""Minimal A-share backtester for evidence-loop validation."""

from __future__ import annotations

import math

from pydantic import BaseModel, Field

from loop_harness.evidence.quant_contracts import QuantBacktestOutput
from loop_harness.quant_data.models import AShareMarketDataSet


class AShareBacktestResult(BaseModel):
    """Normalized result from an A-share backtest."""

    run_id: str
    strategy: str
    parameters: dict[str, int | float | str] = Field(default_factory=dict)
    metrics: QuantBacktestOutput


class AShareBacktester:
    """Small deterministic backtester for baseline evidence generation."""

    def buy_and_hold(self, dataset: AShareMarketDataSet, *, run_id: str) -> AShareBacktestResult:
        """Run a buy-and-hold baseline on close prices."""

        closes = [bar.close for bar in dataset.bars]
        returns = _daily_returns(closes)
        total_return = (closes[-1] / closes[0]) - 1 if len(closes) >= 2 else 0.0
        return AShareBacktestResult(
            run_id=run_id,
            strategy="buy_and_hold",
            parameters={},
            metrics=_metrics_from_returns(
                returns,
                equity_curve=_equity_curve_from_returns(returns),
                total_return=total_return,
                trade_count=1,
                sample_count=len(closes),
            ),
        )

    def moving_average_crossover(
        self,
        dataset: AShareMarketDataSet,
        *,
        run_id: str,
        fast_window: int,
        slow_window: int,
    ) -> AShareBacktestResult:
        """Run a simple moving-average crossover candidate."""

        if fast_window >= slow_window:
            raise ValueError("fast_window must be smaller than slow_window")
        if fast_window <= 0 or slow_window <= 0:
            raise ValueError("moving-average windows must be positive")
        closes = [bar.close for bar in dataset.bars]
        raw_returns = _daily_returns(closes)
        positions = self._positions(closes, fast_window=fast_window, slow_window=slow_window)
        strategy_returns = [
            raw_return * positions[index - 1]
            for index, raw_return in enumerate(raw_returns, start=1)
        ]
        trade_count = sum(1 for index in range(1, len(positions)) if positions[index] != positions[index - 1])
        equity_curve = _equity_curve_from_returns(strategy_returns)
        total_return = equity_curve[-1] - 1 if equity_curve else 0.0
        return AShareBacktestResult(
            run_id=run_id,
            strategy="moving_average_crossover",
            parameters={"fast_window": fast_window, "slow_window": slow_window},
            metrics=_metrics_from_returns(
                strategy_returns,
                equity_curve=equity_curve,
                total_return=total_return,
                trade_count=trade_count,
                sample_count=len(closes),
            ),
        )

    @staticmethod
    def _positions(closes: list[float], *, fast_window: int, slow_window: int) -> list[float]:
        positions: list[float] = []
        for index in range(len(closes)):
            if index + 1 < slow_window:
                positions.append(0.0)
                continue
            fast_avg = sum(closes[index + 1 - fast_window : index + 1]) / fast_window
            slow_avg = sum(closes[index + 1 - slow_window : index + 1]) / slow_window
            positions.append(1.0 if fast_avg > slow_avg else 0.0)
        return positions


def _daily_returns(closes: list[float]) -> list[float]:
    return [(closes[index] / closes[index - 1]) - 1 for index in range(1, len(closes))]


def _equity_curve_from_returns(returns: list[float]) -> list[float]:
    equity = 1.0
    curve: list[float] = []
    for daily_return in returns:
        equity *= 1 + daily_return
        curve.append(equity)
    return curve


def _metrics_from_returns(
    returns: list[float],
    *,
    equity_curve: list[float],
    total_return: float,
    trade_count: int,
    sample_count: int,
) -> QuantBacktestOutput:
    return_count = max(len(returns), 1)
    annual_return = (1 + total_return) ** (252 / return_count) - 1 if total_return > -1 else -1.0
    volatility = _stddev(returns) * math.sqrt(252) if returns else 0.0
    sharpe = annual_return / volatility if volatility > 0 else 0.0
    max_drawdown = _max_drawdown(equity_curve)
    positive_days = sum(1 for value in returns if value > 0)
    win_rate = positive_days / len(returns) if returns else 0.0
    turnover = trade_count / sample_count if sample_count > 0 else 0.0
    return QuantBacktestOutput(
        total_return=round(total_return, 6),
        annual_return=round(annual_return, 6),
        sharpe=round(sharpe, 6),
        max_drawdown=round(max_drawdown, 6),
        volatility=round(volatility, 6),
        win_rate=round(win_rate, 6),
        turnover=round(turnover, 6),
        trade_count=trade_count,
        benchmark_return=0.0,
        excess_return=round(total_return, 6),
        sample_count=sample_count,
    )


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def _max_drawdown(equity_curve: list[float]) -> float:
    peak = 1.0
    max_dd = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak)
    return max_dd
