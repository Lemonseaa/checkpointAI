"""A-share market data providers.

Vendor CSV is the serious path because it preserves provenance and avoids
silent scraping instability. Network/API providers are optional bridges.
"""

from __future__ import annotations

import csv
import math
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Protocol

from loop_harness.quant_data.models import AShareMarketBar, AShareMarketDataSet


class MarketDataProvider(Protocol):
    """Common A-share provider interface."""

    def fetch(
        self,
        *,
        ts_code: str,
        start: date,
        end: date,
        adjusted_mode: str,
    ) -> AShareMarketDataSet:
        """Fetch normalized A-share daily bars."""


class AShareStaticProvider:
    """Deterministic A-share fixture provider for tests and demos only."""

    def fetch(
        self,
        *,
        ts_code: str,
        start: date,
        end: date,
        adjusted_mode: str,
    ) -> AShareMarketDataSet:
        """Return deterministic pseudo A-share prices."""

        bars: list[AShareMarketBar] = []
        current = start
        index = 0
        while current <= end:
            if current.weekday() < 5:
                base = 100.0 + index * 0.08 + math.sin(index / 7.0) * 1.2
                close = round(base, 4)
                bars.append(
                    AShareMarketBar(
                        trade_date=current,
                        open=round(close * 0.995, 4),
                        high=round(close * 1.012, 4),
                        low=round(close * 0.988, 4),
                        close=close,
                        volume=1000000.0 + index * 1000.0,
                        amount=close * (1000000.0 + index * 1000.0),
                    )
                )
                index += 1
            current += timedelta(days=1)
        return AShareMarketDataSet(
            ts_code=ts_code,
            name=None,
            frequency="1d",
            source="static_a_share",
            vendor="fixture",
            license_note="deterministic fixture; not decision-grade data",
            adjusted_mode=adjusted_mode,
            decision_grade=False,
            bars=bars,
        )


class VendorCSVAShareProvider:
    """Load licensed or operator-provided A-share daily data from CSV."""

    REQUIRED_COLUMNS = {"ts_code", "trade_date", "open", "high", "low", "close", "vol"}

    def __init__(self, path: str | Path, *, vendor: str, license_note: str | None = None) -> None:
        self.path = Path(path)
        self.vendor = vendor
        self.license_note = license_note or f"operator-provided export from {vendor}"

    def fetch(
        self,
        *,
        ts_code: str,
        start: date,
        end: date,
        adjusted_mode: str,
    ) -> AShareMarketDataSet:
        """Load and normalize rows from a Tushare-style daily CSV export."""

        with self.path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = set(reader.fieldnames or [])
            missing = sorted(self.REQUIRED_COLUMNS - fieldnames)
            if missing:
                raise ValueError(f"Vendor A-share CSV missing required columns: {', '.join(missing)}")
            bars = [
                self._bar(row)
                for row in reader
                if row.get("ts_code", "").strip() == ts_code
                and start <= self._parse_trade_date(row["trade_date"]) <= end
            ]
        return AShareMarketDataSet(
            ts_code=ts_code,
            name=None,
            frequency="1d",
            source="vendor_csv",
            vendor=self.vendor,
            license_note=self.license_note,
            adjusted_mode=adjusted_mode,
            decision_grade=True,
            bars=sorted(bars, key=lambda bar: bar.trade_date),
        )

    @classmethod
    def _bar(cls, row: dict[str, str]) -> AShareMarketBar:
        return AShareMarketBar(
            trade_date=cls._parse_trade_date(row["trade_date"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["vol"]),
            amount=float(row["amount"]) if row.get("amount") else None,
        )

    @staticmethod
    def _parse_trade_date(raw: str) -> date:
        value = raw.strip()
        if "-" in value:
            return date.fromisoformat(value)
        return datetime.strptime(value, "%Y%m%d").date()


class TushareDailyProvider:
    """Optional Tushare bridge that requires an explicit token.

    This class intentionally does not hide token or dependency problems. Serious
    A-share evidence should fail loudly when the source cannot be proven.
    """

    def __init__(self, token: str) -> None:
        if not token.strip():
            raise ValueError("TushareDailyProvider requires an explicit token")
        self.token = token

    def fetch(
        self,
        *,
        ts_code: str,
        start: date,
        end: date,
        adjusted_mode: str,
    ) -> AShareMarketDataSet:
        """Fetch daily bars through tushare when the package is installed."""

        try:
            import tushare as ts  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("tushare package is not installed") from exc

        pro = ts.pro_api(self.token)
        frame = pro.daily(
            ts_code=ts_code,
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
        )
        rows = frame.to_dict("records")
        bars = [VendorCSVAShareProvider._bar({key: str(value) for key, value in row.items()}) for row in rows]
        return AShareMarketDataSet(
            ts_code=ts_code,
            name=None,
            frequency="1d",
            source="tushare",
            vendor="tushare_pro",
            license_note="Tushare Pro API token required; verify your account permissions.",
            adjusted_mode=adjusted_mode,
            decision_grade=True,
            bars=sorted(bars, key=lambda bar: bar.trade_date),
        )
