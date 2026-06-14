"""Quant platform export adapters for serious backtest evidence."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from loop_harness.evidence.charts import OptimizationChartPayload
from loop_harness.evidence.models import EvidenceReport
from loop_harness.harness import EvidenceHarness


class QuantPlatformMetadata(BaseModel):
    """Metadata describing one external quant platform backtest run."""

    platform: str
    run_id: str
    strategy_name: str
    strategy_version: str | None = None
    universe: list[str] = Field(default_factory=list)
    benchmark: str | None = None
    start_date: str
    end_date: str
    initial_cash: float | None = None
    commission: float | None = None
    slippage: float | None = None
    frequency: str = "daily"
    run_kind: str = "historical"
    parameters: dict[str, Any] = Field(default_factory=dict)


class QuantPlatformExport(BaseModel):
    """Normalized files from one quant platform export directory."""

    export_dir: Path
    metadata: QuantPlatformMetadata
    metrics: dict[str, float]
    equity_curve: list[dict[str, str]]
    trades: list[dict[str, str]]
    positions: list[dict[str, str]]
    logs: str = ""

    REQUIRED_FILES: ClassVar[set[str]] = {
        "metadata.json",
        "metrics.json",
        "equity_curve.csv",
        "trades.csv",
        "positions.csv",
    }

    @classmethod
    def load(cls, export_dir: str | Path) -> QuantPlatformExport:
        """Load and validate one platform export directory."""

        path = Path(export_dir)
        missing = sorted(file_name for file_name in cls.REQUIRED_FILES if not (path / file_name).exists())
        if missing:
            raise ValueError(f"Quant platform export missing required files: {', '.join(missing)}")
        metadata = QuantPlatformMetadata.model_validate(
            json.loads((path / "metadata.json").read_text(encoding="utf-8"))
        )
        raw_metrics = json.loads((path / "metrics.json").read_text(encoding="utf-8"))
        metrics = {
            str(key): float(value)
            for key, value in raw_metrics.items()
            if isinstance(value, int | float)
        }
        logs_path = path / "logs.txt"
        return cls(
            export_dir=path,
            metadata=metadata,
            metrics=metrics,
            equity_curve=_read_csv(path / "equity_curve.csv"),
            trades=_read_csv(path / "trades.csv"),
            positions=_read_csv(path / "positions.csv"),
            logs=logs_path.read_text(encoding="utf-8") if logs_path.exists() else "",
        )


class JoinQuantExportQualityReport(BaseModel):
    """Quality gate result for one JoinQuant export."""

    status: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    sample_count: int


class JoinQuantBatchImportResult(BaseModel):
    """Result from importing a baseline plus candidate JoinQuant exports."""

    baseline_run_id: str
    candidate_run_ids: list[str]
    comparison_reports: list[EvidenceReport]
    chart: OptimizationChartPayload
    markdown: str


class JoinQuantExportAdapter:
    """Convert JoinQuant-style export directories into evidence payloads."""

    def to_payload(
        self,
        export_dir: str | Path,
        *,
        workflow_id: str,
        scenario_id: str,
    ) -> dict[str, Any]:
        """Convert one JoinQuant export directory to Workflow Contract v1."""

        export = QuantPlatformExport.load(export_dir)
        quality = evaluate_joinquant_export_quality(export)
        metadata = export.metadata
        return {
            "workflow_id": workflow_id,
            "run_id": metadata.run_id,
            "scenario_id": scenario_id,
            "run_kind": metadata.run_kind,
            "nodes": [
                {"id": "load_joinquant_export", "name": "Load JoinQuant export", "type": "data"},
                {"id": "parse_backtest_metrics", "name": "Parse backtest metrics", "type": "evaluation"},
                {"id": "parse_trades_positions", "name": "Parse trades and positions", "type": "trace"},
                {"id": "evaluate_risk", "name": "Evaluate risk gates", "type": "evaluation"},
                {"id": "build_report", "name": "Build evidence report", "type": "output"},
            ],
            "edges": [
                {"source": "load_joinquant_export", "target": "parse_backtest_metrics"},
                {"source": "parse_backtest_metrics", "target": "parse_trades_positions"},
                {"source": "parse_trades_positions", "target": "evaluate_risk"},
                {"source": "evaluate_risk", "target": "build_report"},
            ],
            "trace": [
                {
                    "node_id": "load_joinquant_export",
                    "status": "succeeded",
                    "duration_ms": 20,
                    "metrics": {"sample_count": export.metrics.get("sample_count", 0.0)},
                    "output_summary": f"{metadata.platform} export {metadata.run_id}",
                },
                {
                    "node_id": "parse_backtest_metrics",
                    "status": "succeeded",
                    "duration_ms": 20,
                    "metrics": {
                        "sharpe": export.metrics.get("sharpe", 0.0),
                        "max_drawdown": export.metrics.get("max_drawdown", 0.0),
                        "total_return": export.metrics.get("total_return", 0.0),
                    },
                },
                {
                    "node_id": "parse_trades_positions",
                    "status": "succeeded",
                    "duration_ms": 20,
                    "metrics": {
                        "trade_count": float(len(export.trades)),
                        "position_rows": float(len(export.positions)),
                    },
                },
                {
                    "node_id": "evaluate_risk",
                    "status": "succeeded" if quality.status != "blocked" else "warning",
                    "duration_ms": 20,
                    "output_summary": f"quality={quality.status}; blockers={quality.blockers}",
                },
                {"node_id": "build_report", "status": "succeeded", "duration_ms": 10},
            ],
            "metrics": export.metrics,
            "metric_schema": _metric_schema(),
            "config": {
                "platform": metadata.platform,
                "strategy_name": metadata.strategy_name,
                "strategy_version": metadata.strategy_version,
                "parameters": metadata.parameters,
                "benchmark": metadata.benchmark,
                "commission": metadata.commission,
                "slippage": metadata.slippage,
                "initial_cash": metadata.initial_cash,
                "frequency": metadata.frequency,
            },
            "artifacts": [
                {"type": "csv", "path": str(export.export_dir / "equity_curve.csv"), "metadata": {"kind": "equity_curve"}},
                {"type": "csv", "path": str(export.export_dir / "trades.csv"), "metadata": {"kind": "trades"}},
                {"type": "csv", "path": str(export.export_dir / "positions.csv"), "metadata": {"kind": "positions"}},
            ],
            "metadata": {
                "platform": metadata.platform,
                "export_dir": str(export.export_dir),
                "strategy_name": metadata.strategy_name,
                "strategy_version": metadata.strategy_version,
                "universe": metadata.universe,
                "benchmark": metadata.benchmark,
                "start_date": metadata.start_date,
                "end_date": metadata.end_date,
                "quality": quality.model_dump(mode="json"),
                "log_excerpt": export.logs[:500],
            },
        }


class JoinQuantBatchExportImporter:
    """Import a baseline and candidate JoinQuant exports into evidence."""

    def __init__(self, harness: EvidenceHarness) -> None:
        self.harness = harness
        self.adapter = JoinQuantExportAdapter()

    def import_batch(
        self,
        batch_dir: str | Path,
        *,
        workflow_id: str,
        scenario_id: str,
    ) -> JoinQuantBatchImportResult:
        """Import `baseline/` plus candidate subdirectories."""

        root = Path(batch_dir)
        baseline_dir = root / "baseline"
        if not baseline_dir.exists():
            raise ValueError("JoinQuant batch export requires a baseline/ directory")
        baseline_payload = self.adapter.to_payload(
            baseline_dir,
            workflow_id=workflow_id,
            scenario_id=scenario_id,
        )
        self.harness.ingest_payload(baseline_payload)
        baseline_run_id = str(baseline_payload["run_id"])
        candidate_run_ids: list[str] = []
        comparisons: list[EvidenceReport] = []
        for candidate_dir in sorted(path for path in root.iterdir() if path.is_dir() and path.name != "baseline"):
            payload = self.adapter.to_payload(
                candidate_dir,
                workflow_id=workflow_id,
                scenario_id=scenario_id,
            )
            self.harness.ingest_payload(payload)
            candidate_run_id = str(payload["run_id"])
            candidate_run_ids.append(candidate_run_id)
            comparisons.append(self.harness.compare(baseline_run_id, candidate_run_id))
        chart = self.harness.optimization_chart_for_runs(baseline_run_id, candidate_run_ids)
        return JoinQuantBatchImportResult(
            baseline_run_id=baseline_run_id,
            candidate_run_ids=candidate_run_ids,
            comparison_reports=comparisons,
            chart=chart,
            markdown=_batch_markdown(baseline_run_id, candidate_run_ids, comparisons),
        )


def evaluate_joinquant_export_quality(export: QuantPlatformExport) -> JoinQuantExportQualityReport:
    """Evaluate whether a JoinQuant export is strong enough to discuss."""

    blockers: list[str] = []
    warnings: list[str] = []
    metadata = export.metadata
    if not metadata.benchmark:
        blockers.append("missing_benchmark")
    if metadata.commission is None:
        blockers.append("missing_commission")
    if metadata.slippage is None:
        blockers.append("missing_slippage")
    if not export.equity_curve:
        blockers.append("missing_equity_curve")
    if not export.trades:
        blockers.append("missing_trades")
    if not export.positions:
        blockers.append("missing_positions")
    if not metadata.parameters:
        blockers.append("missing_strategy_parameters")
    if metadata.run_kind not in {"historical", "paper"}:
        blockers.append("unsupported_run_kind")
    sample_count = int(export.metrics.get("sample_count", len(export.equity_curve)))
    if sample_count < 120:
        blockers.append("sample_count_below_minimum")
    if _has_abnormal_equity_jump(export.equity_curve):
        warnings.append("abnormal_equity_jump")
    return JoinQuantExportQualityReport(
        status="blocked" if blockers else "valid",
        blockers=blockers,
        warnings=warnings,
        sample_count=sample_count,
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _has_abnormal_equity_jump(rows: list[dict[str, str]]) -> bool:
    previous: float | None = None
    for row in rows:
        try:
            equity = float(row.get("equity", "0"))
        except ValueError:
            continue
        if previous and previous > 0 and abs(equity / previous - 1) > 0.5:
            return True
        previous = equity
    return False


def _metric_schema() -> dict[str, dict[str, object]]:
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
        "volatility": {"direction": "lower", "category": "guardrail", "weight": 0.05},
        "turnover": {"direction": "lower", "category": "system", "weight": 0.0},
        "trade_count": {"direction": "bounded", "category": "data_quality", "weight": 0.0},
        "sample_count": {"direction": "higher", "category": "data_quality", "weight": 0.0},
    }


def _batch_markdown(
    baseline_run_id: str,
    candidate_run_ids: list[str],
    comparisons: list[EvidenceReport],
) -> str:
    lines = [
        "# JoinQuant Export Batch Report",
        "",
        f"Baseline: {baseline_run_id}",
        f"Candidates: {', '.join(candidate_run_ids)}",
        "",
        "## Comparisons",
    ]
    for report in comparisons:
        lines.append(
            f"- {report.candidate_run_id}: recommendation={report.recommendation.value}, "
            f"summary={report.summary}"
        )
    return "\n".join(lines)
