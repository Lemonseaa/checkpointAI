"""Strategy proposal contracts for external quant backtest platforms."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class QuantStrategyType(str, Enum):
    """Supported strategy proposal families."""

    MOVING_AVERAGE_CROSSOVER = "moving_average_crossover"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"


class StrategyRiskConstraints(BaseModel):
    """Risk constraints expected before paper-trading discussion."""

    max_drawdown: float = 0.2
    max_turnover: float | None = None
    min_sample_count: int = 120

    @field_validator("max_drawdown")
    @classmethod
    def ratio_must_be_valid(cls, value: float) -> float:
        """Validate drawdown ratios."""

        if not 0 <= value <= 1:
            raise ValueError("max_drawdown must be between 0 and 1")
        return value

    @field_validator("min_sample_count")
    @classmethod
    def sample_count_must_be_positive(cls, value: int) -> int:
        """Validate minimum sample count."""

        if value <= 0:
            raise ValueError("min_sample_count must be positive")
        return value


class StrategyProposal(BaseModel):
    """A quant strategy change proposal before external backtest execution."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scenario_id: str
    hypothesis: str
    strategy_type: QuantStrategyType
    universe: list[str]
    parameters: dict[str, int | float | str | bool] = Field(default_factory=dict)
    reason: str
    expected_metric: str
    risk_constraints: StrategyRiskConstraints = Field(default_factory=StrategyRiskConstraints)
    run_kind: str = "historical"
    platform_targets: list[str] = Field(default_factory=lambda: ["joinquant", "rqalpha"])
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("scenario_id", "hypothesis", "reason", "expected_metric", "run_kind")
    @classmethod
    def required_text(cls, value: str) -> str:
        """Reject empty contract fields."""

        if not value.strip():
            raise ValueError("scenario_id, hypothesis, reason, expected_metric and run_kind are required")
        return value

    @field_validator("universe", "platform_targets")
    @classmethod
    def non_empty_list(cls, value: list[str]) -> list[str]:
        """Reject empty lists and blank entries."""

        if not value or any(not item.strip() for item in value):
            raise ValueError("universe and platform_targets must be non-empty")
        return value

    @model_validator(mode="after")
    def validate_strategy_parameters(self) -> StrategyProposal:
        """Validate strategy-specific parameters without binding to one platform."""

        if self.strategy_type == QuantStrategyType.MOVING_AVERAGE_CROSSOVER:
            fast_window = _as_int(self.parameters.get("fast_window"), "fast_window")
            slow_window = _as_int(self.parameters.get("slow_window"), "slow_window")
            if fast_window <= 0 or slow_window <= 0:
                raise ValueError("moving average windows must be positive")
            if fast_window >= slow_window:
                raise ValueError("fast_window must be smaller than slow_window")
        elif self.strategy_type == QuantStrategyType.MOMENTUM:
            lookback_window = _as_int(self.parameters.get("lookback_window"), "lookback_window")
            if lookback_window <= 0:
                raise ValueError("lookback_window must be positive")
        elif self.strategy_type == QuantStrategyType.MEAN_REVERSION:
            lookback_window = _as_int(self.parameters.get("lookback_window"), "lookback_window")
            entry_zscore = _as_float(self.parameters.get("entry_zscore"), "entry_zscore")
            if lookback_window <= 0:
                raise ValueError("lookback_window must be positive")
            if entry_zscore <= 0:
                raise ValueError("entry_zscore must be positive")
        return self


class BacktestConfigDraft(BaseModel):
    """Platform-neutral config draft sent to an external backtest runner."""

    platform: str
    proposal_id: str
    scenario_id: str
    strategy_type: str
    universe: list[str]
    parameters: dict[str, int | float | str | bool]
    risk_constraints: dict[str, Any]
    expected_metric: str
    run_kind: str
    notes: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def proposal_to_backtest_config(proposal: StrategyProposal, *, platform: str) -> BacktestConfigDraft:
    """Convert a strategy proposal to a platform config draft."""

    normalized_platform = platform.strip().lower()
    if normalized_platform not in {"joinquant", "rqalpha"}:
        raise ValueError(f"Unsupported quant backtest platform: {platform}")
    notes = (
        "Run this strategy proposal on the external platform, preserve benchmark/fees/slippage, "
        "and export results using the Quant Platform Export Contract."
    )
    return BacktestConfigDraft(
        platform=normalized_platform,
        proposal_id=proposal.id,
        scenario_id=proposal.scenario_id,
        strategy_type=proposal.strategy_type.value,
        universe=proposal.universe,
        parameters=dict(proposal.parameters),
        risk_constraints=proposal.risk_constraints.model_dump(mode="json"),
        expected_metric=proposal.expected_metric,
        run_kind=proposal.run_kind,
        notes=notes,
        metadata={
            "source_proposal_id": proposal.id,
            "hypothesis": proposal.hypothesis,
            "reason": proposal.reason,
            "created_at": proposal.created_at.isoformat(),
        },
    )


def _as_int(value: int | float | str | bool | None, field_name: str) -> int:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field_name} is required")
    try:
        integer_value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc
    if float(integer_value) != float(value):
        raise ValueError(f"{field_name} must be an integer")
    return integer_value


def _as_float(value: int | float | str | bool | None, field_name: str) -> float:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field_name} is required")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
