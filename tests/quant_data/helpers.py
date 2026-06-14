"""Test helpers for quant data fixtures."""

from __future__ import annotations

import csv
import json
from pathlib import Path


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    """Write a small CSV fixture."""

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_joinquant_export(
    path: Path,
    *,
    run_id: str,
    strategy_name: str = "ma_cross",
    sharpe: float = 1.2,
    max_drawdown: float = 0.12,
    total_return: float = 0.18,
    equity_values: list[float] | None = None,
) -> None:
    """Write a JoinQuant-like export directory."""

    path.mkdir(parents=True)
    (path / "metadata.json").write_text(
        json.dumps(
            {
                "platform": "joinquant",
                "run_id": run_id,
                "strategy_name": strategy_name,
                "strategy_version": "v1",
                "universe": ["600519.XSHG"],
                "benchmark": "000300.XSHG",
                "start_date": "2020-01-01",
                "end_date": "2024-12-31",
                "initial_cash": 1000000,
                "commission": 0.0003,
                "slippage": 0.001,
                "frequency": "daily",
                "run_kind": "historical",
                "parameters": {"fast_window": 5, "slow_window": 20},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (path / "metrics.json").write_text(
        json.dumps(
            {
                "total_return": total_return,
                "annual_return": 0.08,
                "sharpe": sharpe,
                "max_drawdown": max_drawdown,
                "volatility": 0.16,
                "win_rate": 0.54,
                "turnover": 0.8,
                "trade_count": 24,
                "benchmark_return": 0.1,
                "excess_return": total_return - 0.1,
                "sample_count": 1000,
            }
        ),
        encoding="utf-8",
    )
    values = equity_values or [1.0, 1.1, 1.05, 1.18]
    write_csv(
        path / "equity_curve.csv",
        ["date", "equity"],
        [{"date": f"2020-01-0{index + 1}", "equity": value} for index, value in enumerate(values)],
    )
    write_csv(
        path / "trades.csv",
        ["datetime", "symbol", "side", "price", "amount", "value"],
        [
            {
                "datetime": "2020-01-02",
                "symbol": "600519.XSHG",
                "side": "buy",
                "price": 100,
                "amount": 100,
                "value": 10000,
            }
        ],
    )
    write_csv(
        path / "positions.csv",
        ["date", "symbol", "amount", "value"],
        [{"date": "2020-01-02", "symbol": "600519.XSHG", "amount": 100, "value": 10000}],
    )
    (path / "logs.txt").write_text("JoinQuant backtest completed\n", encoding="utf-8")
