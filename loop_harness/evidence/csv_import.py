"""CSV importers for external backtest evidence."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from loop_harness.evidence.quant_contracts import QuantBacktestOutput


class QuantCSVImportResult(BaseModel):
    """Result returned after importing quant backtest CSV rows."""

    workflow_id: str
    scenario_id: str
    run_kind: str
    imported_count: int
    run_ids: list[str]
    warning: str = "not_live_trading_evidence: imported historical backtest rows are not live trading proof."


class QuantBacktestCSVImporter:
    """Convert quant backtest CSV rows into Workflow Contract v1 payloads."""

    REQUIRED_COLUMNS = {
        "run_id",
        "fast_window",
        "slow_window",
        "total_return",
        "sharpe",
        "max_drawdown",
        "win_rate",
        "turnover",
        "trade_count",
    }

    def load(
        self,
        path: str | Path,
        *,
        workflow_id: str,
        scenario_id: str,
        run_kind: str,
    ) -> list[dict[str, Any]]:
        """Load CSV rows as ingestable workflow payloads."""

        csv_path = Path(path)
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = set(reader.fieldnames or [])
            missing = sorted(self.REQUIRED_COLUMNS - fieldnames)
            if missing:
                raise ValueError(f"Quant CSV missing required columns: {', '.join(missing)}")
            return [
                self._payload(row, workflow_id=workflow_id, scenario_id=scenario_id, run_kind=run_kind)
                for row in reader
            ]

    def _payload(
        self,
        row: dict[str, str],
        *,
        workflow_id: str,
        scenario_id: str,
        run_kind: str,
    ) -> dict[str, Any]:
        run_id = row["run_id"].strip()
        if not run_id:
            raise ValueError("Quant CSV row has empty run_id")
        fast_window = self._int(row, "fast_window")
        slow_window = self._int(row, "slow_window")
        trade_count = self._int(row, "trade_count")
        sample_count = self._int(row, "sample_count") if row.get("sample_count") else 504
        capital = self._float(row, "capital") if row.get("capital") else None
        total_return = self._float(row, "total_return")
        sharpe = self._float(row, "sharpe")
        max_drawdown = self._float(row, "max_drawdown")
        win_rate = self._float(row, "win_rate")
        turnover = self._float(row, "turnover")
        quant_output = QuantBacktestOutput(
            total_return=total_return,
            annual_return=round(total_return / 2, 6),
            sharpe=sharpe,
            max_drawdown=max_drawdown,
            volatility=self._float(row, "volatility") if row.get("volatility") else 0.0,
            win_rate=win_rate,
            turnover=turnover,
            trade_count=trade_count,
            benchmark_return=self._float(row, "benchmark_return") if row.get("benchmark_return") else 0.0,
            excess_return=self._float(row, "excess_return") if row.get("excess_return") else total_return,
            sample_count=sample_count,
        )
        return {
            "workflow_id": workflow_id,
            "run_id": run_id,
            "scenario_id": scenario_id,
            "run_kind": run_kind,
            "nodes": [
                {"id": "load_data", "name": "Load imported backtest data", "type": "data"},
                {"id": "strategy", "name": "Imported strategy parameters", "type": "strategy"},
                {"id": "risk", "name": "Imported risk metrics", "type": "evaluation"},
                {"id": "report", "name": "Imported backtest report", "type": "output"},
            ],
            "edges": [
                {"source": "load_data", "target": "strategy"},
                {"source": "strategy", "target": "risk"},
                {"source": "risk", "target": "report"},
            ],
            "trace": [
                {"node_id": "load_data", "status": "succeeded", "duration_ms": 20, "metrics": {"sample_count": sample_count}},
                {
                    "node_id": "strategy",
                    "status": "succeeded",
                    "duration_ms": 80,
                    "metrics": {"sharpe": sharpe, "trade_count": float(trade_count)},
                    "output_summary": f"fast_window={fast_window}, slow_window={slow_window}",
                },
                {
                    "node_id": "risk",
                    "status": "succeeded",
                    "duration_ms": 30,
                    "metrics": {"max_drawdown": max_drawdown},
                },
                {"node_id": "report", "status": "succeeded", "duration_ms": 10},
            ],
            "metrics": {
                "total_return": quant_output.total_return,
                "annual_return": quant_output.annual_return,
                "benchmark_return": quant_output.benchmark_return,
                "excess_return": quant_output.excess_return,
                "sharpe": quant_output.sharpe,
                "max_drawdown": quant_output.max_drawdown,
                "win_rate": quant_output.win_rate,
                "turnover": quant_output.turnover,
                "trade_count": float(quant_output.trade_count),
                "sample_count": float(quant_output.sample_count),
                "latency_ms": 140.0,
            },
            "metric_schema": self._metric_schema(),
            "config": {
                "strategy": "csv_imported_backtest",
                "fast_window": fast_window,
                "slow_window": slow_window,
            },
            "artifacts": [],
            "metadata": {
                "data_source": "csv_import",
                "contract": "quant_evidence_v1",
                "importer": "QuantBacktestCSVImporter",
                "source_row": dict(row),
                "capital": capital,
            },
        }

    @staticmethod
    def _metric_schema() -> dict[str, dict[str, Any]]:
        return {
            "total_return": {"direction": "higher", "category": "business", "weight": 0.2},
            "annual_return": {"direction": "higher", "category": "business", "weight": 0.1},
            "benchmark_return": {"direction": "reference", "category": "business", "weight": 0.0},
            "excess_return": {"direction": "higher", "category": "business", "weight": 0.2},
            "sharpe": {"direction": "higher", "category": "business", "weight": 0.3},
            "max_drawdown": {
                "direction": "lower",
                "category": "guardrail",
                "weight": 0.2,
                "threshold": 0.2,
                "is_guardrail": True,
            },
            "win_rate": {"direction": "higher", "category": "business", "weight": 0.05},
            "turnover": {"direction": "lower", "category": "system", "weight": 0.0},
            "trade_count": {"direction": "bounded", "category": "data_quality", "weight": 0.0},
            "sample_count": {"direction": "higher", "category": "data_quality", "weight": 0.0},
            "latency_ms": {"direction": "lower", "category": "system", "weight": 0.0},
        }

    @staticmethod
    def _float(row: dict[str, str], key: str) -> float:
        try:
            return float(row[key])
        except ValueError as exc:
            raise ValueError(f"Quant CSV column {key} must be numeric") from exc

    @staticmethod
    def _int(row: dict[str, str], key: str) -> int:
        try:
            return int(row[key])
        except ValueError as exc:
            raise ValueError(f"Quant CSV column {key} must be an integer") from exc
