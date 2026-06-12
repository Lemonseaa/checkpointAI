"""Quant workflow input and backtest output contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from loop_harness.evidence.contract import ContractIssue, ContractValidationResult


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
    sample_count: int

    @field_validator("max_drawdown", "win_rate")
    @classmethod
    def ratio_must_be_between_zero_and_one(cls, value: float, info: Any) -> float:
        """Validate ratio-style metrics before evidence ingestion."""

        if value < 0 or value > 1:
            raise ValueError(f"{info.field_name} must be between 0 and 1")
        return value

    @field_validator("trade_count", "sample_count")
    @classmethod
    def counts_must_be_positive(cls, value: int, info: Any) -> int:
        """Reject empty backtest windows."""

        if value <= 0:
            raise ValueError(f"{info.field_name} must be positive")
        return value


class QuantEvidenceContractValidator:
    """Validate the quant-specific evidence contract before recommendation."""

    REQUIRED_METRICS = {
        "total_return",
        "max_drawdown",
        "sharpe",
        "win_rate",
        "sample_count",
    }

    def validate(self, payload: dict[str, Any]) -> ContractValidationResult:
        """Return quant-specific validation issues for one workflow payload."""

        issues: list[ContractIssue] = []
        metrics = payload.get("metrics")
        if not isinstance(metrics, dict):
            return ContractValidationResult(
                status="rejected",
                issues=[
                    ContractIssue(
                        code="quant.metrics_missing",
                        field="metrics",
                        severity="error",
                        message="Quant evidence requires a metrics object.",
                    )
                ],
            )

        for metric in sorted(self.REQUIRED_METRICS):
            if metric not in metrics:
                issues.append(
                    ContractIssue(
                        code="quant.metric_missing",
                        field=metric,
                        severity="error",
                        message=f"Quant evidence is missing required metric: {metric}.",
                    )
                )

        for metric in self.REQUIRED_METRICS & metrics.keys():
            if not isinstance(metrics[metric], int | float):
                issues.append(
                    ContractIssue(
                        code="quant.metric_not_numeric",
                        field=metric,
                        severity="error",
                        message=f"Quant metric {metric} must be numeric.",
                    )
                )

        sample_count = metrics.get("sample_count")
        if isinstance(sample_count, int | float) and sample_count < 30:
            issues.append(
                ContractIssue(
                    code="quant.sample_count_low",
                    field="sample_count",
                    severity="warning",
                    message="Quant evidence has low sample_count; recommendations will remain conservative.",
                    details={"minimum": 30, "actual": float(sample_count)},
                )
            )

        max_drawdown = metrics.get("max_drawdown")
        if isinstance(max_drawdown, int | float) and (max_drawdown < 0 or max_drawdown > 1):
            issues.append(
                ContractIssue(
                    code="quant.max_drawdown_invalid",
                    field="max_drawdown",
                    severity="error",
                    message="max_drawdown must be between 0 and 1.",
                    details={"actual": float(max_drawdown)},
                )
            )

        if any(issue.severity == "error" for issue in issues):
            status = "rejected"
        elif issues:
            status = "warning"
        else:
            status = "valid"
        return ContractValidationResult(status=status, issues=issues)
