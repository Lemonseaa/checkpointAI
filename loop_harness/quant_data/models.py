"""Durable contracts for A-share market data used by quant evidence loops."""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class DataSourceKind(str, Enum):
    """Supported A-share market data source kinds."""

    STATIC_A_SHARE = "static_a_share"
    VENDOR_CSV = "vendor_csv"
    TUSHARE = "tushare"


class AShareMarketBar(BaseModel):
    """One daily A-share OHLCV bar."""

    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float = Field(ge=0)
    amount: float | None = None

    @field_validator("open", "high", "low", "close")
    @classmethod
    def price_must_be_positive(cls, value: float) -> float:
        """Reject non-positive prices because they cannot support backtests."""

        if value <= 0:
            raise ValueError("price must be positive")
        return value

    @model_validator(mode="after")
    def validate_price_range(self) -> AShareMarketBar:
        """Ensure OHLC values describe a coherent bar."""

        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be greater than or equal to open, close, and low")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be less than or equal to open, close, and high")
        return self


class MarketDataQualityReport(BaseModel):
    """Quality summary for one market data set."""

    status: str
    sample_count: int
    flags: list[str] = Field(default_factory=list)
    source: str
    vendor: str
    adjusted_mode: str
    decision_grade: bool


class AShareMarketDataSet(BaseModel):
    """Normalized A-share market data set."""

    ts_code: str
    name: str | None = None
    frequency: str = "1d"
    source: str
    vendor: str
    license_note: str
    adjusted_mode: str
    decision_grade: bool
    bars: list[AShareMarketBar]

    @model_validator(mode="after")
    def validate_bars_are_chronological(self) -> AShareMarketDataSet:
        """Reject duplicated or non-chronological trade dates."""

        dates = [bar.trade_date for bar in self.bars]
        if dates != sorted(dates):
            raise ValueError("A-share bars must be chronological by trade_date")
        if len(set(dates)) != len(dates):
            raise ValueError("A-share bars must not contain duplicate trade_date values")
        return self

    @property
    def start_date(self) -> date | None:
        """Return the first available trade date."""

        return self.bars[0].trade_date if self.bars else None

    @property
    def end_date(self) -> date | None:
        """Return the final available trade date."""

        return self.bars[-1].trade_date if self.bars else None

    def quality_report(self, min_bars: int = 120) -> MarketDataQualityReport:
        """Evaluate whether this data set can support serious historical evidence."""

        flags: list[str] = []
        if len(self.bars) < min_bars:
            flags.append("sample_count_below_minimum")
        if self.adjusted_mode == "none":
            flags.append("unadjusted_prices")
        if not self.license_note.strip():
            flags.append("missing_license_note")
        if not self.vendor.strip():
            flags.append("missing_vendor")
        if not self.decision_grade:
            flags.append("not_decision_grade")
        status = "valid" if not flags else "warning"
        return MarketDataQualityReport(
            status=status,
            sample_count=len(self.bars),
            flags=flags,
            source=self.source,
            vendor=self.vendor,
            adjusted_mode=self.adjusted_mode,
            decision_grade=self.decision_grade,
        )
