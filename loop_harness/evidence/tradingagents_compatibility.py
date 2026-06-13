"""Compatibility scoring for TradingAgents real-sample exports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loop_harness.evidence.quant_contracts import QuantEvidenceContractValidator


@dataclass(slots=True)
class TradingAgentsCompatibilityReport:
    """Decision report for whether TradingAgents is ready for adapter work."""

    decision: str
    overall_score: float
    sample_count: int
    real_sample_count: int
    scores: dict[str, float] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


def score_tradingagents_samples(
    converted_payloads: list[dict[str, Any]],
    *,
    min_real_samples: int = 5,
) -> TradingAgentsCompatibilityReport:
    """Score converted TradingAgents samples against adapter-readiness criteria."""

    sample_count = len(converted_payloads)
    real_samples = [payload for payload in converted_payloads if _is_real_sample(payload)]
    blockers: list[str] = []
    recommendations: list[str] = []

    if sample_count == 0:
        return TradingAgentsCompatibilityReport(
            decision="no_go",
            overall_score=0.0,
            sample_count=0,
            real_sample_count=0,
            blockers=["no_samples"],
            recommendations=["Collect sanitized historical TradingAgents exports."],
        )

    if not real_samples:
        blockers.append("fixture_only")
        recommendations.append("Collect real historical exports; fixture samples only validate conversion.")
    elif len(real_samples) < min_real_samples:
        blockers.append("sample_count_below_minimum")
        recommendations.append(f"Collect at least {min_real_samples} real historical exports.")

    if any(not payload.get("trace") for payload in converted_payloads):
        blockers.append("missing_trace")
        recommendations.append("Expose role-level or tool-level trace in every export.")
    if any(not payload.get("config") for payload in converted_payloads):
        blockers.append("missing_config_surface")
        recommendations.append("Expose strategy parameters in every export config.")
    if any(_missing_core_metrics(payload) for payload in converted_payloads):
        blockers.append("missing_core_metrics")
        recommendations.append("Include total_return, sharpe, max_drawdown, win_rate, and sample_count.")

    scores = {
        "input_output": _score_has_fields(converted_payloads, ["workflow_id", "run_id", "scenario_id"]),
        "trace_coverage": _score_non_empty(converted_payloads, "trace"),
        "business_metrics": _score_core_metrics(converted_payloads),
        "config_surface": _score_non_empty(converted_payloads, "config"),
        "artifact_quality": _score_non_empty(converted_payloads, "artifacts"),
        "prompt_control": _score_prompt_control(converted_payloads),
        "integration_effort": 0.5 if blockers else 1.0,
    }
    raw_score = round(sum(scores.values()) / len(scores), 4)
    overall_score = min(raw_score, 0.4) if not real_samples else raw_score
    return TradingAgentsCompatibilityReport(
        decision=_decision(blockers, len(real_samples), min_real_samples),
        overall_score=overall_score,
        sample_count=sample_count,
        real_sample_count=len(real_samples),
        scores=scores,
        blockers=sorted(set(blockers)),
        recommendations=sorted(set(recommendations)),
    )


def _decision(blockers: list[str], real_sample_count: int, min_real_samples: int) -> str:
    blocker_set = set(blockers)
    if "no_samples" in blocker_set or "fixture_only" in blocker_set:
        return "no_go"
    if blocker_set & {"missing_trace", "missing_config_surface", "missing_core_metrics"}:
        return "needs_mapping_fix"
    if real_sample_count < min_real_samples:
        return "needs_more_samples"
    return "go"


def _is_real_sample(payload: dict[str, Any]) -> bool:
    run_kind = str(payload.get("run_kind", "")).lower()
    metadata = payload.get("metadata")
    data_source = ""
    if isinstance(metadata, dict):
        data_source = str(metadata.get("data_source", "")).lower()
    if run_kind in {"fixture", "synthetic"}:
        return False
    return not any(token in data_source for token in ("fixture", "synthetic", "mock", "demo"))


def _missing_core_metrics(payload: dict[str, Any]) -> list[str]:
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        return sorted(QuantEvidenceContractValidator.REQUIRED_METRICS)
    return sorted(metric for metric in QuantEvidenceContractValidator.REQUIRED_METRICS if metric not in metrics)


def _score_has_fields(payloads: list[dict[str, Any]], fields: list[str]) -> float:
    if not payloads:
        return 0.0
    complete = sum(1 for payload in payloads if all(payload.get(field) for field in fields))
    return round(complete / len(payloads), 4)


def _score_non_empty(payloads: list[dict[str, Any]], field: str) -> float:
    if not payloads:
        return 0.0
    complete = sum(1 for payload in payloads if bool(payload.get(field)))
    return round(complete / len(payloads), 4)


def _score_core_metrics(payloads: list[dict[str, Any]]) -> float:
    if not payloads:
        return 0.0
    complete = sum(1 for payload in payloads if not _missing_core_metrics(payload))
    return round(complete / len(payloads), 4)


def _score_prompt_control(payloads: list[dict[str, Any]]) -> float:
    if not payloads:
        return 0.0
    prompt_ready = 0.0
    for payload in payloads:
        metadata = payload.get("metadata")
        if isinstance(metadata, dict) and metadata.get("prompt_slots"):
            prompt_ready += 1.0
        elif payload.get("config"):
            prompt_ready += 0.5
    return round(prompt_ready / len(payloads), 4)
