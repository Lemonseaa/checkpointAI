"""Evidence evaluation for V3 recommendation decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loop_harness.metrics import ComparisonResult


class EvidenceDecision(str, Enum):
    """Evidence-level decision."""

    IMPROVED = "improved"
    WORSE = "worse"
    INCONCLUSIVE = "inconclusive"


class RecommendedAction(str, Enum):
    """Human-facing next action after evidence evaluation."""

    APPROVE_FOR_SHADOW_OR_PAPER = "approve_for_shadow_or_paper"
    COLLECT_MORE_EVIDENCE = "collect_more_evidence"
    REJECT = "reject"


@dataclass(slots=True)
class EvidenceEvaluation:
    """Result of evaluating one schema-aware comparison."""

    decision: EvidenceDecision
    recommended_action: RecommendedAction
    confidence: float
    reason: str
    objective_score: float
    guardrail_violations: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


class EvidenceEvaluationEngine:
    """Evaluate whether one comparison contains enough evidence to recommend action."""

    def __init__(
        self,
        min_sample_count: int = 30,
        min_confidence: float = 0.6,
        min_objective_score: float = 0.05,
    ) -> None:
        """Create a conservative V3.1 evidence evaluator."""

        self.min_sample_count = min_sample_count
        self.min_confidence = min_confidence
        self.min_objective_score = min_objective_score

    def evaluate(self, comparison: ComparisonResult) -> EvidenceEvaluation:
        """Evaluate one comparison result."""

        sample_count = self._sample_count(comparison.provenance)
        confidence = self._confidence(comparison, sample_count)
        evidence = {
            "run_kind": comparison.run_kind,
            "sample_count": sample_count,
            "data_source": comparison.provenance.get("data_source"),
            "business_metric_count": len(comparison.business_metric_diffs),
        }
        data_source = str(comparison.provenance.get("data_source", "")).lower()
        if comparison.guardrail_violations:
            return EvidenceEvaluation(
                decision=EvidenceDecision.WORSE,
                recommended_action=RecommendedAction.REJECT,
                confidence=max(confidence, 0.8),
                reason=(
                    "Guardrail violation blocks recommendation: "
                    f"{', '.join(comparison.guardrail_violations)}."
                ),
                objective_score=comparison.objective_score,
                guardrail_violations=list(comparison.guardrail_violations),
                evidence=evidence,
            )
        if comparison.run_kind in {"fixture", "synthetic"}:
            return EvidenceEvaluation(
                decision=EvidenceDecision.INCONCLUSIVE,
                recommended_action=RecommendedAction.COLLECT_MORE_EVIDENCE,
                confidence=confidence,
                reason=f"{comparison.run_kind} evidence can validate the loop but cannot justify recommendation.",
                objective_score=comparison.objective_score,
                evidence=evidence,
            )
        if self._non_decision_data_source(data_source):
            return EvidenceEvaluation(
                decision=EvidenceDecision.INCONCLUSIVE,
                recommended_action=RecommendedAction.COLLECT_MORE_EVIDENCE,
                confidence=confidence,
                reason=f"data_source={data_source} is not decision-grade evidence.",
                objective_score=comparison.objective_score,
                evidence=evidence,
            )
        if sample_count < self.min_sample_count:
            return EvidenceEvaluation(
                decision=EvidenceDecision.INCONCLUSIVE,
                recommended_action=RecommendedAction.COLLECT_MORE_EVIDENCE,
                confidence=confidence,
                reason=f"sample_count={sample_count} is below minimum {self.min_sample_count}.",
                objective_score=comparison.objective_score,
                evidence=evidence,
            )
        if comparison.objective_score <= -self.min_objective_score or not comparison.improved:
            return EvidenceEvaluation(
                decision=EvidenceDecision.WORSE,
                recommended_action=RecommendedAction.REJECT,
                confidence=confidence,
                reason=f"{comparison.run_kind} evidence is worse; objective_score={comparison.objective_score:.6f}.",
                objective_score=comparison.objective_score,
                evidence=evidence,
            )
        if comparison.objective_score >= self.min_objective_score and confidence >= self.min_confidence:
            return EvidenceEvaluation(
                decision=EvidenceDecision.IMPROVED,
                recommended_action=RecommendedAction.APPROVE_FOR_SHADOW_OR_PAPER,
                confidence=confidence,
                reason=f"{comparison.run_kind} evidence improved with enough samples.",
                objective_score=comparison.objective_score,
                evidence=evidence,
            )
        return EvidenceEvaluation(
            decision=EvidenceDecision.INCONCLUSIVE,
            recommended_action=RecommendedAction.COLLECT_MORE_EVIDENCE,
            confidence=confidence,
            reason=(
                "Evidence is not strong enough for recommendation; "
                f"objective_score={comparison.objective_score:.6f}, confidence={confidence:.2f}."
            ),
            objective_score=comparison.objective_score,
            evidence=evidence,
        )

    @staticmethod
    def _sample_count(provenance: dict[str, Any]) -> int:
        value = provenance.get("sample_count", 0)
        if isinstance(value, int | float):
            return int(value)
        return 0

    def _confidence(self, comparison: ComparisonResult, sample_count: int) -> float:
        run_kind_factor = {
            "fixture": 0.1,
            "synthetic": 0.25,
            "historical": 0.75,
            "paper": 0.85,
            "live": 0.95,
        }.get(comparison.run_kind, 0.4)
        sample_factor = min(1.0, sample_count / max(1, self.min_sample_count))
        metric_factor = min(1.0, len(comparison.business_metric_diffs) / 3.0)
        score_factor = min(1.0, abs(comparison.objective_score) / max(self.min_objective_score, 0.01))
        return round((run_kind_factor * 0.45) + (sample_factor * 0.25) + (metric_factor * 0.2) + (score_factor * 0.1), 4)

    @staticmethod
    def _non_decision_data_source(data_source: str) -> bool:
        if not data_source:
            return False
        blocked_tokens = ("fixture", "synthetic", "mock", "demo")
        return any(token in data_source for token in blocked_tokens)
