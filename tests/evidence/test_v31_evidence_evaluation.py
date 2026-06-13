"""V3.1 evidence evaluation tests."""

from __future__ import annotations

import unittest

from loop_harness.evaluation import (
    EvidenceDecision,
    EvidenceEvaluationEngine,
    RecommendedAction,
)
from loop_harness.metrics import ComparisonResult


class V31EvidenceEvaluationTest(unittest.TestCase):
    """Validate evidence decisions before recommendation algorithms exist."""

    def test_historical_improvement_with_enough_samples_recommends_approval(self) -> None:
        engine = EvidenceEvaluationEngine(min_sample_count=30, min_confidence=0.6)
        comparison = ComparisonResult(
            objective_score=0.42,
            improved=True,
            business_metric_diffs={"sharpe": 0.8, "max_drawdown": -0.03},
            run_kind="historical",
            provenance={"sample_count": 60, "data_source": "vendor_historical_prices"},
        )

        decision = engine.evaluate(comparison)

        self.assertEqual(decision.decision, EvidenceDecision.IMPROVED)
        self.assertGreaterEqual(decision.confidence, 0.6)
        self.assertEqual(decision.recommended_action, RecommendedAction.APPROVE_FOR_SHADOW_OR_PAPER)
        self.assertIn("historical", decision.reason)

    def test_synthetic_improvement_stays_inconclusive(self) -> None:
        engine = EvidenceEvaluationEngine(min_sample_count=30)
        comparison = ComparisonResult(
            objective_score=0.9,
            improved=True,
            business_metric_diffs={"sharpe": 3.0},
            run_kind="synthetic",
            provenance={"sample_count": 260, "data_source": "synthetic_prices"},
        )

        decision = engine.evaluate(comparison)

        self.assertEqual(decision.decision, EvidenceDecision.INCONCLUSIVE)
        self.assertEqual(decision.recommended_action, RecommendedAction.COLLECT_MORE_EVIDENCE)
        self.assertIn("synthetic", decision.reason)

    def test_fixture_improvement_stays_inconclusive(self) -> None:
        engine = EvidenceEvaluationEngine(min_sample_count=30)
        comparison = ComparisonResult(
            objective_score=0.9,
            improved=True,
            business_metric_diffs={"sharpe": 3.0},
            run_kind="fixture",
            provenance={"sample_count": 260, "data_source": "tradingagents_fixture"},
        )

        decision = engine.evaluate(comparison)

        self.assertEqual(decision.decision, EvidenceDecision.INCONCLUSIVE)
        self.assertEqual(decision.recommended_action, RecommendedAction.COLLECT_MORE_EVIDENCE)
        self.assertIn("fixture", decision.reason)

    def test_historical_run_with_fixture_source_stays_inconclusive(self) -> None:
        engine = EvidenceEvaluationEngine(min_sample_count=30)
        comparison = ComparisonResult(
            objective_score=0.9,
            improved=True,
            business_metric_diffs={"sharpe": 3.0},
            run_kind="historical",
            provenance={"sample_count": 260, "data_source": "fixture_history"},
        )

        decision = engine.evaluate(comparison)

        self.assertEqual(decision.decision, EvidenceDecision.INCONCLUSIVE)
        self.assertEqual(decision.recommended_action, RecommendedAction.COLLECT_MORE_EVIDENCE)
        self.assertIn("not decision-grade", decision.reason)

    def test_guardrail_violation_blocks_even_when_score_improves(self) -> None:
        engine = EvidenceEvaluationEngine(min_sample_count=30)
        comparison = ComparisonResult(
            objective_score=0.5,
            improved=True,
            business_metric_diffs={"total_return": 0.1, "max_drawdown": 0.09},
            guardrail_violations=["max_drawdown"],
            run_kind="historical",
            provenance={"sample_count": 90, "data_source": "vendor_historical_prices"},
        )

        decision = engine.evaluate(comparison)

        self.assertEqual(decision.decision, EvidenceDecision.WORSE)
        self.assertEqual(decision.recommended_action, RecommendedAction.REJECT)
        self.assertIn("max_drawdown", decision.reason)

    def test_low_sample_count_stays_inconclusive(self) -> None:
        engine = EvidenceEvaluationEngine(min_sample_count=30)
        comparison = ComparisonResult(
            objective_score=0.2,
            improved=True,
            business_metric_diffs={"sharpe": 0.2},
            run_kind="historical",
            provenance={"sample_count": 12, "data_source": "vendor_historical_prices"},
        )

        decision = engine.evaluate(comparison)

        self.assertEqual(decision.decision, EvidenceDecision.INCONCLUSIVE)
        self.assertEqual(decision.recommended_action, RecommendedAction.COLLECT_MORE_EVIDENCE)
        self.assertIn("sample_count", decision.reason)

    def test_negative_objective_score_is_worse(self) -> None:
        engine = EvidenceEvaluationEngine(min_sample_count=30)
        comparison = ComparisonResult(
            objective_score=-0.15,
            improved=False,
            business_metric_diffs={"sharpe": -0.2},
            run_kind="paper",
            provenance={"sample_count": 45, "data_source": "paper_trading"},
        )

        decision = engine.evaluate(comparison)

        self.assertEqual(decision.decision, EvidenceDecision.WORSE)
        self.assertEqual(decision.recommended_action, RecommendedAction.REJECT)
        self.assertGreater(decision.confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
