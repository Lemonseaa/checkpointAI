"""Quant platform export adapters for serious backtest evidence."""

from __future__ import annotations

import csv
import json
import re
import shutil
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


class SensitiveFinding(BaseModel):
    """Sensitive data finding inside an external export."""

    file_name: str
    pattern: str
    excerpt: str


class JoinQuantExportDiagnosis(BaseModel):
    """Human-readable diagnosis for one JoinQuant export directory."""

    export_dir: str
    run_id: str | None = None
    ready_to_import: bool
    repairable: bool
    missing_files: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    field_mappings: dict[str, dict[str, str]] = Field(default_factory=dict)
    sensitive_findings: list[SensitiveFinding] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class JoinQuantBatchImportResult(BaseModel):
    """Result from importing a baseline plus candidate JoinQuant exports."""

    baseline_run_id: str
    candidate_run_ids: list[str]
    quality_reports: dict[str, JoinQuantExportQualityReport]
    import_readiness_summary: dict[str, Any]
    comparison_reports: list[EvidenceReport]
    chart: OptimizationChartPayload
    curve_payload: dict[str, Any]
    paper_trading_discussion: str
    markdown: str


class JoinQuantRealDrillSummary(BaseModel):
    """End-to-end JoinQuant real-data drill summary."""

    workflow_id: str
    scenario_id: str
    batch_dir: str
    normalize_dir: str | None = None
    json_path: str | None = None
    markdown_path: str | None = None
    diagnosed_count: int
    normalized_count: int
    ready_count: int
    blocked_count: int
    field_issue_stats: dict[str, Any]
    diagnoses: list[JoinQuantExportDiagnosis]
    batch_result: JoinQuantBatchImportResult | None = None
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
        loaded_exports = preflight_joinquant_batch(root)
        baseline_export = loaded_exports[0][1]
        candidate_exports = loaded_exports[1:]
        exports_by_run_id = {export.metadata.run_id: export for _, export, _ in loaded_exports}
        quality_reports = {export.metadata.run_id: quality for _, export, quality in loaded_exports}
        readiness_summary = _import_readiness_summary(loaded_exports)
        baseline_payload = self.adapter.to_payload(
            baseline_export.export_dir,
            workflow_id=workflow_id,
            scenario_id=scenario_id,
        )
        self.harness.ingest_payload(baseline_payload)
        baseline_run_id = str(baseline_payload["run_id"])
        candidate_run_ids: list[str] = []
        comparisons: list[EvidenceReport] = []
        for candidate_dir, _candidate_export, _quality in candidate_exports:
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
        curve_payload = build_joinquant_curve_payload(exports_by_run_id, baseline_run_id, candidate_run_ids)
        paper_trading_discussion = _paper_trading_discussion(quality_reports, comparisons)
        return JoinQuantBatchImportResult(
            baseline_run_id=baseline_run_id,
            candidate_run_ids=candidate_run_ids,
            quality_reports=quality_reports,
            import_readiness_summary=readiness_summary,
            comparison_reports=comparisons,
            chart=chart,
            curve_payload=curve_payload,
            paper_trading_discussion=paper_trading_discussion,
            markdown=_batch_markdown(
                baseline_run_id,
                candidate_run_ids,
                comparisons,
                quality_reports,
                paper_trading_discussion,
            ),
        )


class JoinQuantRealDrillRunner:
    """Run a safe JoinQuant batch drill before the UI consumes results."""

    def __init__(self, harness: EvidenceHarness) -> None:
        self.harness = harness

    def run(
        self,
        batch_dir: str | Path,
        *,
        workflow_id: str,
        scenario_id: str,
        normalize_dir: str | Path | None = None,
        output_json_path: str | Path | None = None,
        output_markdown_path: str | Path | None = None,
    ) -> JoinQuantRealDrillSummary:
        """Diagnose, optionally normalize, validate, import, and summarize one batch."""

        root = Path(batch_dir)
        export_dirs = _joinquant_batch_dirs(root)
        diagnoses = [diagnose_joinquant_export(export_dir) for export_dir in export_dirs]
        initial_field_issue_stats = _field_issue_stats(diagnoses)
        normalized_count = 0
        import_root = root

        if normalize_dir is not None:
            normalized_root = Path(normalize_dir)
            for export_dir, diagnosis in zip(export_dirs, diagnoses, strict=True):
                if diagnosis.repairable and not diagnosis.sensitive_findings:
                    normalize_joinquant_export(export_dir, normalized_root / export_dir.name)
                    normalized_count += 1
            import_root = normalized_root
            export_dirs = _joinquant_batch_dirs(import_root)
            diagnoses = [diagnose_joinquant_export(export_dir) for export_dir in export_dirs]

        field_issue_stats = _merge_field_issue_stats(initial_field_issue_stats, _field_issue_stats(diagnoses))
        ready_count = sum(1 for diagnosis in diagnoses if diagnosis.ready_to_import)
        blocked_count = len(diagnoses) - ready_count
        batch_result: JoinQuantBatchImportResult | None = None
        if diagnoses and blocked_count == 0:
            batch_result = JoinQuantBatchExportImporter(self.harness).import_batch(
                import_root,
                workflow_id=workflow_id,
                scenario_id=scenario_id,
            )
        markdown = _real_drill_markdown(
            workflow_id=workflow_id,
            scenario_id=scenario_id,
            batch_dir=root,
            normalize_dir=Path(normalize_dir) if normalize_dir is not None else None,
            diagnoses=diagnoses,
            normalized_count=normalized_count,
            field_issue_stats=field_issue_stats,
            batch_result=batch_result,
        )
        summary = JoinQuantRealDrillSummary(
            workflow_id=workflow_id,
            scenario_id=scenario_id,
            batch_dir=str(root),
            normalize_dir=str(normalize_dir) if normalize_dir is not None else None,
            json_path=str(output_json_path) if output_json_path is not None else None,
            markdown_path=str(output_markdown_path) if output_markdown_path is not None else None,
            diagnosed_count=len(diagnoses),
            normalized_count=normalized_count,
            ready_count=ready_count,
            blocked_count=blocked_count,
            field_issue_stats=field_issue_stats,
            diagnoses=diagnoses,
            batch_result=batch_result,
            markdown=markdown,
        )
        _write_real_drill_artifacts(summary, output_json_path, output_markdown_path)
        return summary


def diagnose_joinquant_export(export_dir: str | Path) -> JoinQuantExportDiagnosis:
    """Diagnose whether one JoinQuant export can be imported or normalized."""

    path = Path(export_dir)
    missing = sorted(file_name for file_name in QuantPlatformExport.REQUIRED_FILES if not (path / file_name).exists())
    sensitive_findings = _scan_sensitive_data(path)
    sensitive_blockers = [f"sensitive_data:{finding.pattern}" for finding in sensitive_findings]
    field_mappings = {
        "equity_curve.csv": _field_mappings_for_csv(path / "equity_curve.csv"),
        "trades.csv": _field_mappings_for_csv(path / "trades.csv"),
        "positions.csv": _field_mappings_for_csv(path / "positions.csv"),
    }
    field_mappings = {file_name: mapping for file_name, mapping in field_mappings.items() if mapping}
    if missing:
        return JoinQuantExportDiagnosis(
            export_dir=str(path),
            ready_to_import=False,
            repairable=False,
            missing_files=missing,
            blockers=[f"missing_required_file:{file_name}" for file_name in missing] + sensitive_blockers,
            field_mappings=field_mappings,
            sensitive_findings=sensitive_findings,
            recommendations=["Re-export the missing files before import."],
        )
    try:
        export = QuantPlatformExport.load(path)
        quality = evaluate_joinquant_export_quality(export)
    except (OSError, ValueError) as exc:
        return JoinQuantExportDiagnosis(
            export_dir=str(path),
            ready_to_import=False,
            repairable=False,
            blockers=[str(exc), *sensitive_blockers],
            field_mappings=field_mappings,
            sensitive_findings=sensitive_findings,
            recommendations=["Fix the export structure or regenerate the JoinQuant export."],
        )
    blockers = quality.blockers + sorted(set(sensitive_blockers))
    return JoinQuantExportDiagnosis(
        export_dir=str(path),
        run_id=export.metadata.run_id,
        ready_to_import=quality.status != "blocked" and not sensitive_findings,
        repairable=not missing,
        blockers=blockers,
        warnings=quality.warnings,
        field_mappings=field_mappings,
        sensitive_findings=sensitive_findings,
        recommendations=_diagnosis_recommendations(quality, field_mappings, sensitive_findings),
    )


def normalize_joinquant_export(export_dir: str | Path, output_dir: str | Path) -> JoinQuantExportDiagnosis:
    """Write a standard Quant Platform Export Contract copy."""

    source = Path(export_dir)
    target = Path(output_dir)
    diagnosis = diagnose_joinquant_export(source)
    if not diagnosis.repairable:
        raise ValueError("JoinQuant export is not repairable: " + "; ".join(diagnosis.blockers))
    if diagnosis.sensitive_findings:
        raise ValueError("JoinQuant export contains sensitive data: " + "; ".join(diagnosis.blockers))
    target.mkdir(parents=True, exist_ok=True)
    for file_name in ["metadata.json", "metrics.json"]:
        shutil.copyfile(source / file_name, target / file_name)
    logs_path = source / "logs.txt"
    if logs_path.exists():
        shutil.copyfile(logs_path, target / "logs.txt")
    _write_csv(target / "equity_curve.csv", ["date", "equity"], _read_csv(source / "equity_curve.csv"))
    _write_csv(
        target / "trades.csv",
        ["datetime", "symbol", "side", "price", "amount", "value"],
        _read_csv(source / "trades.csv"),
    )
    _write_csv(
        target / "positions.csv",
        ["date", "symbol", "amount", "value"],
        _read_csv(source / "positions.csv"),
    )
    return diagnose_joinquant_export(target)


def preflight_joinquant_batch(
    batch_dir: str | Path,
) -> list[tuple[Path, QuantPlatformExport, JoinQuantExportQualityReport]]:
    """Load and quality-check a JoinQuant batch before any evidence is stored."""

    root = Path(batch_dir)
    baseline_dir = root / "baseline"
    if not baseline_dir.exists():
        raise ValueError("JoinQuant batch preflight failed: missing baseline/ directory")
    candidate_dirs = sorted(path for path in root.iterdir() if path.is_dir() and path.name != "baseline")
    if not candidate_dirs:
        raise ValueError("JoinQuant batch preflight failed: at least one candidate directory is required")
    errors: list[str] = []
    loaded: list[tuple[Path, QuantPlatformExport, JoinQuantExportQualityReport]] = []
    for export_dir in [baseline_dir, *candidate_dirs]:
        try:
            diagnosis = diagnose_joinquant_export(export_dir)
            if diagnosis.sensitive_findings:
                errors.append(f"{export_dir.name}: blocked sensitive data {diagnosis.blockers}")
                continue
            export = QuantPlatformExport.load(export_dir)
            quality = evaluate_joinquant_export_quality(export)
        except (OSError, ValueError) as exc:
            errors.append(f"{export_dir.name}: {exc}")
            continue
        if quality.status == "blocked":
            errors.append(f"{export_dir.name}: blocked quality gates {quality.blockers}")
        loaded.append((export_dir, export, quality))
    if errors:
        raise ValueError("JoinQuant batch preflight failed: " + "; ".join(errors))
    return loaded


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


def build_joinquant_curve_payload(
    exports_by_run_id: dict[str, QuantPlatformExport],
    baseline_run_id: str,
    candidate_run_ids: list[str],
) -> dict[str, Any]:
    """Build equity and drawdown chart data for imported JoinQuant exports."""

    equity_curves: list[dict[str, Any]] = []
    drawdown_curves: list[dict[str, Any]] = []
    ordered_run_ids = [baseline_run_id, *candidate_run_ids]
    for run_id in ordered_run_ids:
        export = exports_by_run_id.get(run_id)
        if export is None:
            continue
        role = "baseline" if run_id == baseline_run_id else "candidate"
        running_peak: float | None = None
        for index, row in enumerate(export.equity_curve):
            equity = _to_float(row.get("equity"))
            if equity is None:
                continue
            running_peak = equity if running_peak is None else max(running_peak, equity)
            drawdown = 0.0 if running_peak <= 0 else (running_peak - equity) / running_peak
            point_date = row.get("date") or row.get("trade_date") or str(index)
            equity_curves.append(
                {
                    "run_id": run_id,
                    "role": role,
                    "date": point_date,
                    "equity": equity,
                }
            )
            drawdown_curves.append(
                {
                    "run_id": run_id,
                    "role": role,
                    "date": point_date,
                    "drawdown": drawdown,
                }
            )
    return {
        "baseline_run_id": baseline_run_id,
        "candidate_run_ids": candidate_run_ids,
        "equity_curves": equity_curves,
        "drawdown_curves": drawdown_curves,
    }


def _joinquant_batch_dirs(root: Path) -> list[Path]:
    baseline_dir = root / "baseline"
    if not baseline_dir.exists():
        raise ValueError("JoinQuant batch drill failed: missing baseline/ directory")
    candidate_dirs = sorted(path for path in root.iterdir() if path.is_dir() and path.name != "baseline")
    if not candidate_dirs:
        raise ValueError("JoinQuant batch drill failed: at least one candidate directory is required")
    return [baseline_dir, *candidate_dirs]


_SENSITIVE_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone_cn": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "api_token": re.compile(
        r"(?i)(api[_-]?key|token|secret|access[_-]?key)\s*[:=]\s*[\"']?[\w.\-]{6,}"
    ),
    "account_id": re.compile(r"(?i)(account[_-]?id|broker[_-]?account)\s*[:=]\s*[\"']?[\w.\-]{4,}"),
    "order_id": re.compile(r"(?i)(order[_-]?id|broker[_-]?order)\s*[:=]\s*[\"']?[\w.\-]{4,}"),
}


def _scan_sensitive_data(export_dir: Path) -> list[SensitiveFinding]:
    findings: list[SensitiveFinding] = []
    file_names = [
        "metadata.json",
        "metrics.json",
        "equity_curve.csv",
        "trades.csv",
        "positions.csv",
        "logs.txt",
    ]
    for file_name in file_names:
        file_path = export_dir / file_name
        if not file_path.exists() or not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern_name, pattern in _SENSITIVE_PATTERNS.items():
            match = pattern.search(text)
            if match:
                findings.append(
                    SensitiveFinding(
                        file_name=file_name,
                        pattern=pattern_name,
                        excerpt=_redacted_excerpt(match.group(0)),
                    )
                )
    return findings


def _redacted_excerpt(value: str) -> str:
    trimmed = value[:80]
    if ":" in trimmed:
        prefix = trimmed.split(":", 1)[0]
        return f"{prefix}:***"
    if "=" in trimmed:
        prefix = trimmed.split("=", 1)[0]
        return f"{prefix}=***"
    return "***"


def _field_issue_stats(diagnoses: list[JoinQuantExportDiagnosis]) -> dict[str, Any]:
    alias_mappings: dict[str, int] = {}
    missing_files: dict[str, int] = {}
    blockers: dict[str, int] = {}
    sensitive_patterns: dict[str, int] = {}
    for diagnosis in diagnoses:
        for mapping in diagnosis.field_mappings.values():
            for alias, standard in mapping.items():
                key = f"{alias}->{standard}"
                alias_mappings[key] = alias_mappings.get(key, 0) + 1
        for file_name in diagnosis.missing_files:
            missing_files[file_name] = missing_files.get(file_name, 0) + 1
        for blocker in diagnosis.blockers:
            blockers[blocker] = blockers.get(blocker, 0) + 1
        for finding in diagnosis.sensitive_findings:
            sensitive_patterns[finding.pattern] = sensitive_patterns.get(finding.pattern, 0) + 1
    return {
        "alias_mappings": alias_mappings,
        "missing_files": missing_files,
        "blockers": blockers,
        "sensitive_patterns": sensitive_patterns,
    }


def _write_real_drill_artifacts(
    summary: JoinQuantRealDrillSummary,
    output_json_path: str | Path | None,
    output_markdown_path: str | Path | None,
) -> None:
    if output_json_path is not None:
        json_path = Path(output_json_path)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if output_markdown_path is not None:
        markdown_path = Path(output_markdown_path)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(summary.markdown, encoding="utf-8")


def _merge_field_issue_stats(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for group_name in ["alias_mappings", "missing_files", "blockers", "sensitive_patterns"]:
        merged_group: dict[str, int] = {}
        for source in [left.get(group_name, {}), right.get(group_name, {})]:
            if not isinstance(source, dict):
                continue
            for key, value in source.items():
                if isinstance(key, str) and isinstance(value, int):
                    merged_group[key] = merged_group.get(key, 0) + value
        merged[group_name] = merged_group
    return merged


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    return [_normalize_csv_row(path.name, row) for row in rows]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _field_mappings_for_csv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for standard, aliases in _csv_aliases(path.name).items():
        for alias in aliases:
            if alias in fieldnames and alias not in used:
                used.add(alias)
                if alias != standard:
                    mapping[alias] = standard
                break
    return mapping


def _normalize_csv_row(file_name: str, row: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    used: set[str] = set()
    for standard, aliases in _csv_aliases(file_name).items():
        for alias in aliases:
            value = row.get(alias)
            if value is not None and alias not in used:
                normalized[standard] = value
                used.add(alias)
                break
    return normalized or row


def _csv_aliases(file_name: str) -> dict[str, list[str]]:
    if file_name == "equity_curve.csv":
        return {
            "date": ["date", "trade_date", "trade_dt", "datetime"],
            "equity": ["equity", "portfolio_value", "total_value", "net_value"],
        }
    if file_name == "trades.csv":
        return {
            "datetime": ["datetime", "trade_dt", "trade_date", "date"],
            "symbol": ["symbol", "code", "security", "order_book_id"],
            "side": ["side", "action", "direction"],
            "price": ["price", "avg_price"],
            "amount": ["quantity", "shares", "amount"],
            "value": ["value", "amount", "turnover"],
        }
    if file_name == "positions.csv":
        return {
            "date": ["date", "trade_date", "trade_dt", "datetime"],
            "symbol": ["symbol", "code", "security", "order_book_id"],
            "amount": ["shares", "quantity", "amount"],
            "value": ["value", "market_value", "portfolio_value"],
        }
    return {}


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


def _to_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


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
    quality_reports: dict[str, JoinQuantExportQualityReport],
    paper_trading_discussion: str,
) -> str:
    lines = [
        "# JoinQuant Export Batch Report",
        "",
        f"Baseline: {baseline_run_id}",
        f"Candidates: {', '.join(candidate_run_ids)}",
        "",
        "## Quality",
    ]
    for run_id, quality in quality_reports.items():
        lines.append(
            f"- {run_id}: status={quality.status}, sample_count={quality.sample_count}, "
            f"blockers={quality.blockers}, warnings={quality.warnings}"
        )
    lines.extend(
        [
            "",
            "## Paper Trading Discussion",
            paper_trading_discussion,
            "",
        ]
    )
    lines.extend(
        [
        "## Comparisons",
        ]
    )
    for report in comparisons:
        lines.append(
            f"- {report.candidate_run_id}: recommendation={report.recommendation.value}, "
            f"summary={report.summary}"
        )
    return "\n".join(lines)


def _import_readiness_summary(
    loaded_exports: list[tuple[Path, QuantPlatformExport, JoinQuantExportQualityReport]],
) -> dict[str, Any]:
    blocked_reasons: dict[str, int] = {}
    ready_count = 0
    for _path, _export, quality in loaded_exports:
        if quality.status == "blocked":
            for blocker in quality.blockers:
                blocked_reasons[blocker] = blocked_reasons.get(blocker, 0) + 1
        else:
            ready_count += 1
    return {
        "ready_count": ready_count,
        "blocked_count": len(loaded_exports) - ready_count,
        "blocked_reasons": blocked_reasons,
        "total_count": len(loaded_exports),
    }


def _diagnosis_recommendations(
    quality: JoinQuantExportQualityReport,
    field_mappings: dict[str, dict[str, str]],
    sensitive_findings: list[SensitiveFinding],
) -> list[str]:
    recommendations: list[str] = []
    if sensitive_findings:
        recommendations.append("Remove sensitive data before import.")
    if field_mappings:
        recommendations.append("Run joinquant-normalize to write a standard contract copy.")
    if quality.blockers:
        recommendations.append("Fix quality blockers before batch import.")
    if not recommendations:
        recommendations.append("Export is ready to import.")
    return recommendations


def _real_drill_markdown(
    *,
    workflow_id: str,
    scenario_id: str,
    batch_dir: Path,
    normalize_dir: Path | None,
    diagnoses: list[JoinQuantExportDiagnosis],
    normalized_count: int,
    field_issue_stats: dict[str, Any],
    batch_result: JoinQuantBatchImportResult | None,
) -> str:
    ready_count = sum(1 for diagnosis in diagnoses if diagnosis.ready_to_import)
    blocked_count = len(diagnoses) - ready_count
    lines = [
        "# JoinQuant Real Data Drill Report",
        "",
        f"workflow_id: {workflow_id}",
        f"scenario_id: {scenario_id}",
        f"batch_dir: {batch_dir}",
        f"normalize_dir: {normalize_dir}" if normalize_dir is not None else "normalize_dir: none",
        f"diagnosed_count: {len(diagnoses)}",
        f"normalized_count: {normalized_count}",
        f"ready_count: {ready_count}",
        f"blocked_count: {blocked_count}",
        "",
        "## Diagnosis",
    ]
    for diagnosis in diagnoses:
        run_label = diagnosis.run_id or Path(diagnosis.export_dir).name
        lines.append(
            f"- {run_label}: ready={diagnosis.ready_to_import}, blockers={diagnosis.blockers}, "
            f"warnings={diagnosis.warnings}"
        )
    lines.extend(["", "## Field Issue Stats"])
    for group_name in ["alias_mappings", "missing_files", "blockers", "sensitive_patterns"]:
        group = field_issue_stats.get(group_name, {})
        lines.append(f"- {group_name}: {group if group else '{}'}")
    lines.extend(["", "## Batch Result"])
    if batch_result is None:
        lines.append("No import was executed because at least one export is blocked.")
    else:
        lines.append(f"- baseline_run_id: {batch_result.baseline_run_id}")
        lines.append(f"- candidate_run_ids: {batch_result.candidate_run_ids}")
        lines.append(f"- paper_trading_discussion: {batch_result.paper_trading_discussion}")
    return "\n".join(lines)


def _paper_trading_discussion(
    quality_reports: dict[str, JoinQuantExportQualityReport],
    comparisons: list[EvidenceReport],
) -> str:
    blocked = [run_id for run_id, quality in quality_reports.items() if quality.status == "blocked"]
    if blocked:
        return (
            "Do not discuss paper trading yet. The following JoinQuant exports failed evidence quality gates: "
            f"{', '.join(blocked)}."
        )
    if not comparisons:
        return "No candidate strategy was imported, so there is no paper-trading candidate to discuss."
    candidates = [
        report.candidate_run_id
        for report in comparisons
        if report.candidate_run_id is not None
        and report.recommendation.value in {"approve", "continue_shadow"}
    ]
    if not candidates:
        return (
            "No candidate is strong enough for paper trading discussion. Keep generating historical evidence "
            "or revise the strategy proposal."
        )
    return (
        "Paper trading can be discussed for the strongest historical candidates, but this is not live-trading "
        f"approval. Candidate(s) to review: {', '.join(candidates)}."
    )
