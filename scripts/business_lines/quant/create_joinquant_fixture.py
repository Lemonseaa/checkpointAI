"""Create a deterministic JoinQuant-style export batch for local acceptance."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def create_joinquant_fixture(output_dir: str | Path) -> Path:
    """Create a baseline plus candidate JoinQuant export fixture."""

    root = Path(output_dir)
    _write_export(
        root / "baseline",
        run_id="jq_fixture_baseline",
        total_return=0.1,
        sharpe=0.8,
        max_drawdown=0.12,
        parameters={"fast_window": 20, "slow_window": 60},
        equity_values=[1.0, 1.03, 1.01, 1.08, 1.1],
    )
    _write_export(
        root / "ma_5_20",
        run_id="jq_fixture_ma_5_20",
        total_return=0.18,
        sharpe=1.2,
        max_drawdown=0.1,
        parameters={"fast_window": 5, "slow_window": 20},
        equity_values=[1.0, 1.05, 1.04, 1.14, 1.18],
    )
    _write_export(
        root / "ma_10_60",
        run_id="jq_fixture_ma_10_60",
        total_return=0.13,
        sharpe=0.95,
        max_drawdown=0.16,
        parameters={"fast_window": 10, "slow_window": 60},
        equity_values=[1.0, 1.04, 0.98, 1.1, 1.13],
    )
    return root


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description="Create a deterministic JoinQuant export fixture batch.")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    output_dir = create_joinquant_fixture(args.output_dir)
    print(f"JoinQuant fixture written to {output_dir}")
    return 0


def _write_export(
    path: Path,
    *,
    run_id: str,
    total_return: float,
    sharpe: float,
    max_drawdown: float,
    parameters: dict[str, int],
    equity_values: list[float],
) -> None:
    path.mkdir(parents=True, exist_ok=True)
    metadata: dict[str, Any] = {
        "platform": "joinquant",
        "run_id": run_id,
        "strategy_name": "fixture_ma_cross",
        "strategy_version": "fixture-v1",
        "universe": ["600519.XSHG"],
        "benchmark": "000300.XSHG",
        "start_date": "2020-01-01",
        "end_date": "2024-12-31",
        "initial_cash": 1000000,
        "commission": 0.0003,
        "slippage": 0.001,
        "frequency": "daily",
        "run_kind": "historical",
        "parameters": parameters,
    }
    metrics = {
        "total_return": total_return,
        "annual_return": total_return / 2,
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
    (path / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (path / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(
        path / "equity_curve.csv",
        ["date", "equity"],
        [{"date": f"2020-01-{index + 1:02d}", "equity": value} for index, value in enumerate(equity_values)],
    )
    _write_csv(
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
    _write_csv(
        path / "positions.csv",
        ["date", "symbol", "amount", "value"],
        [{"date": "2020-01-02", "symbol": "600519.XSHG", "amount": 100, "value": 10000}],
    )
    (path / "logs.txt").write_text("Fixture JoinQuant backtest completed\n", encoding="utf-8")


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


if __name__ == "__main__":
    raise SystemExit(main())
