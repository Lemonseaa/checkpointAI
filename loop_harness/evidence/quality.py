"""Evidence quality gate for external workflow runs."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from loop_harness.evidence.models import ExternalWorkflowRun, WorkflowVisualization


class EvidenceQualityStatus(str, Enum):
    """Trust status for one evidence report."""

    ACCEPTED = "accepted"
    WARNING = "warning"
    REJECTED = "rejected"


class EvidenceQualityResult(BaseModel):
    """Human-readable evidence quality result."""

    status: EvidenceQualityStatus
    score: float
    reasons: list[str] = Field(default_factory=list)


class EvidenceQualityGate:
    """Small deterministic gate before evidence is trusted."""

    min_sample_count: int = 30
    min_trace_coverage: float = 0.8
    min_metric_coverage: float = 0.5

    def evaluate(self, run: ExternalWorkflowRun, visualization: WorkflowVisualization) -> EvidenceQualityResult:
        """Score one run's evidence quality."""

        reasons: list[str] = []
        score = 1.0
        sample_count = int(run.metrics.get("sample_count", 0))
        data_source = str(run.metadata.get("data_source", "")).lower()

        if visualization.trace_coverage < self.min_trace_coverage:
            reasons.append("low_trace_coverage")
            score -= 0.25
        if visualization.metric_coverage < self.min_metric_coverage:
            reasons.append("low_metric_coverage")
            score -= 0.2
        if visualization.black_box_node_ids:
            reasons.append("black_box_nodes_present")
            score -= 0.2
        if run.run_kind.value == "fixture":
            reasons.append("fixture_not_real_evidence")
            score -= 0.55
        elif self._non_decision_data_source(data_source):
            reasons.append("non_decision_data_source")
            score -= 0.45
        elif run.run_kind.value == "synthetic" and sample_count < self.min_sample_count:
            reasons.append("synthetic_low_sample")
            score -= 0.35
        elif sample_count and sample_count < self.min_sample_count:
            reasons.append("low_sample_count")
            score -= 0.2

        normalized_score = max(0.0, min(1.0, round(score, 4)))
        if (
            "fixture_not_real_evidence" in reasons
            or "non_decision_data_source" in reasons
            or "synthetic_low_sample" in reasons
            or normalized_score < 0.5
        ):
            status = EvidenceQualityStatus.REJECTED
        elif reasons:
            status = EvidenceQualityStatus.WARNING
        else:
            status = EvidenceQualityStatus.ACCEPTED

        return EvidenceQualityResult(status=status, score=normalized_score, reasons=reasons)

    @staticmethod
    def _non_decision_data_source(data_source: str) -> bool:
        if not data_source:
            return False
        blocked_tokens = ("fixture", "synthetic", "mock", "demo")
        return any(token in data_source for token in blocked_tokens)
