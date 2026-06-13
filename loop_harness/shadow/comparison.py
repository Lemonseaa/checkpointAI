"""Schema-aware metric comparison for shadow runs."""

from __future__ import annotations

from enum import Enum
from typing import Any

from loop_harness.metrics import (
    ComparisonResult,
    MetricCategory,
    MetricDirection,
    MetricEvaluation,
    MetricSchema,
    MetricSchemaRegistry,
)


class RunKind(str, Enum):
    """Evidence source type for one run."""

    FIXTURE = "fixture"
    SYNTHETIC = "synthetic"
    HISTORICAL = "historical"
    PAPER = "paper"
    LIVE = "live"


class MetricComparator:
    """Compare metrics using direction, category, and guardrail schemas."""

    def __init__(self, registry: MetricSchemaRegistry | None = None) -> None:
        self.registry = registry or MetricSchemaRegistry.default_quant()

    def compare(
        self,
        baseline_metrics: dict[str, Any],
        candidate_metrics: dict[str, Any],
        run_kind: RunKind = RunKind.SYNTHETIC,
        provenance: dict[str, Any] | None = None,
    ) -> ComparisonResult:
        """Compare candidate metrics to baseline metrics."""

        metric_diffs: dict[str, float] = {}
        business_diffs: dict[str, float] = {}
        system_diffs: dict[str, float] = {}
        data_quality_diffs: dict[str, float] = {}
        evaluations: dict[str, MetricEvaluation] = {}
        weighted_score = 0.0
        total_weight = 0.0
        guardrail_violations: list[str] = []

        for name, candidate_value in candidate_metrics.items():
            baseline_value = baseline_metrics.get(name)
            if not isinstance(candidate_value, int | float) or not isinstance(baseline_value, int | float):
                continue
            schema = self.registry.schema_for(name)
            raw_diff = round(float(candidate_value) - float(baseline_value), 10)
            normalized = self._normalized_change(schema, float(baseline_value), float(candidate_value))
            evaluation = MetricEvaluation(
                name=name,
                baseline=float(baseline_value),
                candidate=float(candidate_value),
                raw_diff=raw_diff,
                normalized_change=normalized,
                direction=schema.direction,
                category=schema.category,
                improved=normalized > 0,
            )
            evaluations[name] = evaluation
            metric_diffs[name] = raw_diff
            self._bucket_diff(schema.category, name, raw_diff, business_diffs, system_diffs, data_quality_diffs)
            if schema.is_guardrail and self._violates_guardrail(schema, float(candidate_value)):
                guardrail_violations.append(name)
            if schema.category in {MetricCategory.BUSINESS, MetricCategory.GUARDRAIL} and schema.weight > 0:
                weighted_score += normalized * schema.weight
                total_weight += schema.weight

        objective_score = round(weighted_score / total_weight, 10) if total_weight else 0.0
        improved = objective_score > 0 and not guardrail_violations
        return ComparisonResult(
            metric_diffs=metric_diffs,
            business_metric_diffs=business_diffs,
            system_metric_diffs=system_diffs,
            data_quality_metric_diffs=data_quality_diffs,
            metric_evaluations=evaluations,
            objective_score=objective_score,
            guardrail_violations=guardrail_violations,
            improved=improved,
            summary=self._summary(run_kind, objective_score, improved, guardrail_violations),
            run_kind=run_kind.value,
            provenance=provenance or {},
        )

    @staticmethod
    def _normalized_change(schema: MetricSchema, baseline: float, candidate: float) -> float:
        if schema.direction == MetricDirection.LOWER:
            return round(baseline - candidate, 10)
        if schema.direction == MetricDirection.REFERENCE:
            return 0.0
        if schema.direction == MetricDirection.BOUNDED:
            if schema.threshold is None:
                return 0.0
            return round(-abs(candidate - schema.threshold), 10)
        return round(candidate - baseline, 10)

    @staticmethod
    def _violates_guardrail(schema: MetricSchema, candidate: float) -> bool:
        if schema.threshold is None:
            return False
        if schema.direction == MetricDirection.LOWER:
            return candidate > schema.threshold
        if schema.direction == MetricDirection.HIGHER:
            return candidate < schema.threshold
        return False

    @staticmethod
    def _bucket_diff(
        category: MetricCategory,
        name: str,
        raw_diff: float,
        business: dict[str, float],
        system: dict[str, float],
        data_quality: dict[str, float],
    ) -> None:
        if category in {MetricCategory.BUSINESS, MetricCategory.GUARDRAIL}:
            business[name] = raw_diff
        elif category == MetricCategory.SYSTEM:
            system[name] = raw_diff
        elif category == MetricCategory.DATA_QUALITY:
            data_quality[name] = raw_diff

    @staticmethod
    def _summary(
        run_kind: RunKind,
        objective_score: float,
        improved: bool,
        guardrail_violations: list[str],
    ) -> str:
        status = "improved" if improved else "not improved"
        guardrails = (
            " no guardrail violations"
            if not guardrail_violations
            else f" guardrail violations={guardrail_violations}"
        )
        return f"{run_kind.value} comparison {status}; objective_score={objective_score:.6f};{guardrails}."
