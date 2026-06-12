"""Quant workflow input and backtest output contracts."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class QuantRunInput(BaseModel):
    """Human-owned quant research request contract."""

    capital: float
    universe: list[str]
    start_date: str
    end_date: str
    frequency: str
    risk_limits: dict[str, float] = Field(default_factory=dict)
    objective_metric: str

    @field_validator("capital")
    @classmethod
    def capital_must_be_positive(cls, value: float) -> float:
        """Reject empty capital inputs."""

        if value <= 0:
            raise ValueError("capital must be positive")
        return value


class QuantBacktestOutput(BaseModel):
    """Normalized quant backtest result contract."""

    total_return: float
    annual_return: float
    sharpe: float
    max_drawdown: float
    volatility: float
    win_rate: float
    turnover: float
    trade_count: int
    benchmark_return: float
    excess_return: float
