"""Batch A-share quant experiments driven by sample manifests."""

from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import BaseModel, Field

from loop_harness.harness import EvidenceHarness
from loop_harness.quant_data.manifest import AShareSampleManifest, AShareSampleManifestEntry
from loop_harness.quant_data.models import MarketDataQualityReport
from loop_harness.quant_data.pipeline import AShareQuantLoopPipeline, AShareQuantLoopResult
from loop_harness.quant_data.providers import VendorCSVAShareProvider


class AShareQualitySummary(BaseModel):
    """Quality summary for a manifest of A-share samples."""

    total_symbols: int
    decision_grade_symbols: int
    non_decision_grade_symbols: int
    by_symbol: dict[str, MarketDataQualityReport]


class AShareParameterGrid(BaseModel):
    """Parameter grid for moving-average crossover experiments."""

    fast_windows: list[int] = Field(default_factory=lambda: [5, 10, 20])
    slow_windows: list[int] = Field(default_factory=lambda: [20, 60, 120])

    def pairs(self) -> list[tuple[int, int]]:
        """Return valid fast/slow pairs."""

        return [
            (fast, slow)
            for fast in self.fast_windows
            for slow in self.slow_windows
            if fast < slow
        ]


class AShareBatchRunItem(BaseModel):
    """One symbol/parameter run in a batch experiment."""

    ts_code: str
    name: str | None
    fast_window: int
    slow_window: int
    baseline_run_id: str
    candidate_run_id: str
    recommendation: str
    objective_score: float | None
    total_return: float | None
    sharpe: float | None
    max_drawdown: float | None
    quality_status: str
    quality_flags: list[str] = Field(default_factory=list)


class AShareBatchRunResult(BaseModel):
    """Human-facing result from an A-share batch grid run."""

    symbol_count: int
    run_count: int
    items: list[AShareBatchRunItem]
    quality_summary: AShareQualitySummary
    recommendation_distribution: dict[str, int]
    best_candidates: list[AShareBatchRunItem]
    chart_payload: dict[str, Any]
    markdown: str


def summarize_manifest_quality(
    manifest: AShareSampleManifest,
    *,
    min_bars: int = 120,
) -> AShareQualitySummary:
    """Read every manifest CSV and summarize whether it can support evidence."""

    by_symbol: dict[str, MarketDataQualityReport] = {}
    decision_grade = 0
    for entry in manifest.entries:
        dataset = _dataset_for_entry(entry)
        report = dataset.quality_report(min_bars=min_bars)
        by_symbol[entry.ts_code] = report
        if report.decision_grade and report.status == "valid":
            decision_grade += 1
    return AShareQualitySummary(
        total_symbols=len(manifest.entries),
        decision_grade_symbols=decision_grade,
        non_decision_grade_symbols=len(manifest.entries) - decision_grade,
        by_symbol=by_symbol,
    )


class AShareBatchQuantRunner:
    """Run A-share batch experiments through the existing evidence harness."""

    def __init__(self, harness: EvidenceHarness) -> None:
        self.harness = harness

    def run_grid(
        self,
        manifest: AShareSampleManifest,
        *,
        grid: AShareParameterGrid,
        scenario_id: str,
        run_kind: str,
    ) -> AShareBatchRunResult:
        """Run every manifest entry against every valid parameter pair."""

        quality_summary = summarize_manifest_quality(manifest)
        items: list[AShareBatchRunItem] = []
        for entry in manifest.entries:
            dataset = _dataset_for_entry(entry)
            for fast_window, slow_window in grid.pairs():
                workflow_id = _workflow_id(entry.ts_code, fast_window, slow_window)
                loop_result = AShareQuantLoopPipeline(self.harness).run(
                    dataset,
                    workflow_id=workflow_id,
                    scenario_id=scenario_id,
                    run_kind=run_kind,
                    fast_window=fast_window,
                    slow_window=slow_window,
                )
                items.append(_item(entry, loop_result, fast_window, slow_window))
        recommendation_distribution = dict(Counter(item.recommendation for item in items))
        best_candidates = _best_candidates(items)
        chart_payload = _chart_payload(items, quality_summary)
        return AShareBatchRunResult(
            symbol_count=len(manifest.entries),
            run_count=len(items),
            items=items,
            quality_summary=quality_summary,
            recommendation_distribution=recommendation_distribution,
            best_candidates=best_candidates,
            chart_payload=chart_payload,
            markdown=_markdown(items, quality_summary, recommendation_distribution, best_candidates),
        )


def _dataset_for_entry(entry: AShareSampleManifestEntry) -> Any:
    provider = VendorCSVAShareProvider(
        entry.resolved_path,
        vendor=entry.source_vendor,
        license_note=entry.license_note,
    )
    dataset = provider.fetch(
        ts_code=entry.ts_code,
        start=entry.start_date,
        end=entry.end_date,
        adjusted_mode=entry.adjusted_mode,
    )
    return dataset.model_copy(
        update={
            "name": entry.name,
            "decision_grade": entry.decision_grade,
            "license_note": entry.license_note,
        }
    )


def _item(
    entry: AShareSampleManifestEntry,
    loop_result: AShareQuantLoopResult,
    fast_window: int,
    slow_window: int,
) -> AShareBatchRunItem:
    point = loop_result.chart.candidate_points[0]
    return AShareBatchRunItem(
        ts_code=entry.ts_code,
        name=entry.name,
        fast_window=fast_window,
        slow_window=slow_window,
        baseline_run_id=loop_result.baseline_run_id,
        candidate_run_id=loop_result.candidate_run_id,
        recommendation=loop_result.comparison.recommendation.value,
        objective_score=point.objective_score,
        total_return=point.total_return,
        sharpe=point.sharpe,
        max_drawdown=point.max_drawdown,
        quality_status=loop_result.data_quality.status,
        quality_flags=loop_result.data_quality.flags,
    )


def _workflow_id(ts_code: str, fast_window: int, slow_window: int) -> str:
    return f"a_share_quant_{ts_code.replace('.', '_')}_ma_{fast_window}_{slow_window}"


def _best_candidates(items: list[AShareBatchRunItem]) -> list[AShareBatchRunItem]:
    best_by_symbol: dict[str, AShareBatchRunItem] = {}
    for item in items:
        current = best_by_symbol.get(item.ts_code)
        if current is None or _score(item) > _score(current):
            best_by_symbol[item.ts_code] = item
    return sorted(best_by_symbol.values(), key=_score, reverse=True)


def _score(item: AShareBatchRunItem) -> float:
    return item.objective_score if item.objective_score is not None else -999.0


def _chart_payload(items: list[AShareBatchRunItem], quality: AShareQualitySummary) -> dict[str, Any]:
    symbol_ranking = [
        {
            "ts_code": item.ts_code,
            "name": item.name,
            "fast_window": item.fast_window,
            "slow_window": item.slow_window,
            "objective_score": item.objective_score,
            "sharpe": item.sharpe,
            "max_drawdown": item.max_drawdown,
            "recommendation": item.recommendation,
        }
        for item in _best_candidates(items)
    ]
    parameter_heatmap = [
        {
            "ts_code": item.ts_code,
            "fast_window": item.fast_window,
            "slow_window": item.slow_window,
            "objective_score": item.objective_score,
            "sharpe": item.sharpe,
            "total_return": item.total_return,
        }
        for item in items
    ]
    quality_distribution = Counter(report.status for report in quality.by_symbol.values())
    recommendation_distribution = Counter(item.recommendation for item in items)
    drawdown_blockers = [
        {
            "ts_code": item.ts_code,
            "candidate_run_id": item.candidate_run_id,
            "max_drawdown": item.max_drawdown,
        }
        for item in items
        if item.max_drawdown is not None and item.max_drawdown > 0.2
    ]
    return {
        "symbol_ranking": symbol_ranking,
        "parameter_heatmap": parameter_heatmap,
        "quality_distribution": dict(quality_distribution),
        "recommendation_distribution": dict(recommendation_distribution),
        "drawdown_blockers": drawdown_blockers,
    }


def _markdown(
    items: list[AShareBatchRunItem],
    quality: AShareQualitySummary,
    recommendation_distribution: dict[str, int],
    best_candidates: list[AShareBatchRunItem],
) -> str:
    lines = [
        "# A-Share Batch Quant Report",
        "",
        f"Tested symbols: {quality.total_symbols}",
        f"Decision-grade symbols: {quality.decision_grade_symbols}",
        f"Total candidate runs: {len(items)}",
        f"Recommendation distribution: {recommendation_distribution}",
        "",
        "## Best Candidate Per Symbol",
    ]
    for item in best_candidates:
        label = f"{item.ts_code} {item.name or ''}".strip()
        lines.append(
            f"- {label}: fast={item.fast_window}, slow={item.slow_window}, "
            f"score={item.objective_score}, sharpe={item.sharpe}, "
            f"drawdown={item.max_drawdown}, recommendation={item.recommendation}"
        )
    lines.extend(
        [
            "",
            "## Paper Trading Discussion",
            "Historical evidence can support paper-trading discussion only when samples are decision-grade, "
            "guardrails are not violated, and the recommendation is not inconclusive.",
        ]
    )
    return "\n".join(lines)
