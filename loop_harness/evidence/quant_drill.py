"""Deterministic quant backtest drill for R2 evidence validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from loop_harness.evidence.models import EvidenceReport
from loop_harness.evidence.service import EvidenceService


class QuantDrillResult(BaseModel):
    """Summary of one quant evidence drill run."""

    workflow_id: str
    baseline_run_id: str
    candidate_run_ids: list[str]
    run_count: int
    candidate_count: int
    comparisons: list[EvidenceReport] = Field(default_factory=list)
    report_count: int
    system_findings: list[str] = Field(default_factory=list)
    paper_trade_recommendation: str
    review: dict[str, Any] = Field(default_factory=dict)
    chart_payload: dict[str, Any] = Field(default_factory=dict)
    summary: str


@dataclass(slots=True)
class QuantDrillRunner:
    """Create semi-real historical quant runs and review the evidence chain."""

    service: EvidenceService
    workflow_id: str = "quant_backtest_v1"
    baseline_run_id: str = "quant_baseline_drill"

    def run(self, candidate_count: int = 30, comparison_count: int = 5) -> QuantDrillResult:
        """Run the deterministic quant drill."""

        if candidate_count < 1:
            raise ValueError("candidate_count must be greater than 0")
        if comparison_count < 1:
            raise ValueError("comparison_count must be greater than 0")

        baseline_payload = self._payload(
            run_id=self.baseline_run_id,
            fast_window=8,
            slow_window=21,
            total_return=0.18,
            sharpe=0.92,
            max_drawdown=0.145,
            win_rate=0.53,
            trade_count=82,
            turnover=1.8,
            latency_ms=540,
            stability_score=0.72,
        )
        self.service.ingest_payload(baseline_payload)

        candidate_ids: list[str] = []
        candidate_payloads: list[dict[str, Any]] = []
        for index in range(1, candidate_count + 1):
            payload = self._candidate_payload(index)
            candidate_payloads.append(payload)
            self.service.ingest_payload(payload)
            candidate_ids.append(str(payload["run_id"]))

        comparison_ids = self._selected_candidate_ids(candidate_payloads, comparison_count)
        comparisons = [self.service.compare(self.baseline_run_id, candidate_id) for candidate_id in comparison_ids]
        review = self._review(comparisons)
        system_findings = self._system_findings()
        recommendation = self._paper_trade_recommendation(review, system_findings)
        return QuantDrillResult(
            workflow_id=self.workflow_id,
            baseline_run_id=self.baseline_run_id,
            candidate_run_ids=candidate_ids,
            run_count=1 + len(candidate_ids),
            candidate_count=len(candidate_ids),
            comparisons=comparisons,
            report_count=1 + len(candidate_ids) + len(comparisons),
            system_findings=system_findings,
            paper_trade_recommendation=recommendation,
            review=review,
            chart_payload=self._chart_payload(self.baseline_run_id, candidate_payloads, comparisons),
            summary=(
                f"Quant drill created {1 + len(candidate_ids)} historical runs, "
                f"compared {len(comparisons)} candidates, "
                f"paper_trade_recommendation={recommendation}."
            ),
        )

    def run_v2(self, candidate_count: int = 30, comparison_count: int = 5) -> QuantDrillResult:
        """Run an expanded drill with weak and guardrail-violating candidates."""

        if candidate_count < 2:
            raise ValueError("candidate_count must be at least 2 for run_v2")
        base_candidate_count = candidate_count - 1
        result = self.run(
            candidate_count=base_candidate_count,
            comparison_count=min(comparison_count, base_candidate_count),
        )
        weak_payload = self._payload(
            run_id="quant_candidate_drill_weak",
            fast_window=3,
            slow_window=5,
            total_return=0.08,
            sharpe=0.42,
            max_drawdown=0.28,
            win_rate=0.42,
            trade_count=180,
            turnover=4.2,
            latency_ms=690,
            stability_score=0.38,
        )
        self.service.ingest_payload(weak_payload)
        result.candidate_run_ids.append(str(weak_payload["run_id"]))
        result.candidate_count = len(result.candidate_run_ids)
        result.run_count = 1 + result.candidate_count
        candidate_payloads = self._stored_candidate_payloads(result.candidate_run_ids)
        result.chart_payload = self._chart_payload(result.baseline_run_id, candidate_payloads, result.comparisons)
        result.review = {
            **result.review,
            "guardrail_summary": self._guardrail_summary(result.chart_payload["candidates"]),
        }
        result.summary = (
            f"Quant drill v2 created {result.run_count} historical runs, "
            f"including weak and guardrail-violating candidates; "
            f"paper_trade_recommendation={result.paper_trade_recommendation}."
        )
        return result

    def _candidate_payload(self, index: int) -> dict[str, Any]:
        fast_window = 6 + (index % 12)
        slow_window = 18 + (index % 10)
        signal_quality = ((index * 7) % 13) / 100
        penalty = 0.012 if fast_window >= slow_window else 0.0
        total_return = round(0.17 + signal_quality + (index % 5) * 0.006 - penalty, 4)
        sharpe = round(0.86 + ((index * 5) % 17) / 20 - penalty * 2, 4)
        max_drawdown = round(0.09 + ((index * 3) % 11) / 100, 4)
        win_rate = round(0.49 + ((index * 2) % 12) / 100, 4)
        trade_count = 56 + (index * 9) % 96
        turnover = round(1.1 + ((index * 4) % 18) / 10, 4)
        latency_ms = 500 + (index * 11) % 160
        stability_score = round(0.62 + ((index * 3) % 15) / 100, 4)
        return self._payload(
            run_id=f"quant_candidate_drill_{index:03d}",
            fast_window=fast_window,
            slow_window=slow_window,
            total_return=total_return,
            sharpe=sharpe,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            trade_count=trade_count,
            turnover=turnover,
            latency_ms=latency_ms,
            stability_score=stability_score,
        )

    def _payload(
        self,
        *,
        run_id: str,
        fast_window: int,
        slow_window: int,
        total_return: float,
        sharpe: float,
        max_drawdown: float,
        win_rate: float,
        trade_count: int,
        turnover: float,
        latency_ms: int,
        stability_score: float,
    ) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "run_id": run_id,
            "scenario_id": "quant",
            "run_kind": "historical",
            "nodes": [
                {"id": "load_data", "name": "Load market data", "type": "data"},
                {"id": "feature_engineering", "name": "Feature engineering", "type": "transform"},
                {"id": "strategy", "name": "Moving average strategy", "type": "strategy"},
                {"id": "broker", "name": "Broker simulation", "type": "external", "metadata": {"black_box": True}},
                {"id": "risk", "name": "Risk metrics", "type": "evaluation"},
                {"id": "report", "name": "Backtest report", "type": "output"},
            ],
            "edges": [
                {"source": "load_data", "target": "feature_engineering"},
                {"source": "feature_engineering", "target": "strategy"},
                {"source": "strategy", "target": "broker"},
                {"source": "broker", "target": "risk"},
                {"source": "risk", "target": "report"},
            ],
            "trace": [
                {
                    "node_id": "load_data",
                    "status": "succeeded",
                    "duration_ms": 120,
                    "metrics": {"sample_count": 504},
                },
                {"node_id": "feature_engineering", "status": "succeeded", "duration_ms": 180},
                {
                    "node_id": "strategy",
                    "status": "succeeded",
                    "duration_ms": latency_ms - 200,
                    "metrics": {"sharpe": sharpe, "trade_count": float(trade_count)},
                },
                {
                    "node_id": "risk",
                    "status": "succeeded",
                    "duration_ms": 90,
                    "metrics": {"max_drawdown": max_drawdown, "stability_score": stability_score},
                },
                {"node_id": "report", "status": "succeeded", "duration_ms": 70},
            ],
            "metrics": {
                "total_return": total_return,
                "annual_return": round(total_return / 2, 4),
                "benchmark_return": 0.14,
                "excess_return": round(total_return - 0.14, 4),
                "sharpe": sharpe,
                "max_drawdown": max_drawdown,
                "win_rate": win_rate,
                "trade_count": float(trade_count),
                "turnover": turnover,
                "stability_score": stability_score,
                "sample_count": 504,
                "latency_ms": float(latency_ms),
            },
            "metric_schema": self._metric_schema(),
            "config": {
                "strategy": "moving_average",
                "fast_window": fast_window,
                "slow_window": slow_window,
                "transaction_cost_bps": 8,
            },
            "artifacts": [{"type": "csv", "path": f"artifacts/{run_id}.csv"}],
            "metadata": {
                "data_source": "semi_real_fixture_history",
                "market_universe": "large_cap_demo",
                "period": "2024-01-01..2025-12-31",
            },
        }

    @staticmethod
    def _metric_schema() -> dict[str, dict[str, Any]]:
        return {
            "total_return": {"direction": "higher", "category": "business", "weight": 0.18},
            "annual_return": {"direction": "higher", "category": "business", "weight": 0.08},
            "benchmark_return": {"direction": "reference", "category": "business", "weight": 0.0},
            "excess_return": {"direction": "higher", "category": "business", "weight": 0.22},
            "sharpe": {"direction": "higher", "category": "business", "weight": 0.27},
            "max_drawdown": {
                "direction": "lower",
                "category": "guardrail",
                "weight": 0.2,
                "threshold": 0.2,
                "is_guardrail": True,
            },
            "win_rate": {"direction": "higher", "category": "business", "weight": 0.05},
            "trade_count": {"direction": "bounded", "category": "data_quality", "weight": 0.0, "threshold": 80},
            "turnover": {"direction": "lower", "category": "system", "weight": 0.0},
            "stability_score": {"direction": "higher", "category": "business", "weight": 0.1},
            "sample_count": {"direction": "higher", "category": "data_quality", "weight": 0.0},
            "latency_ms": {"direction": "lower", "category": "system", "weight": 0.0},
        }

    @staticmethod
    def _selected_candidate_ids(payloads: list[dict[str, Any]], count: int) -> list[str]:
        sorted_payloads = sorted(
            payloads,
            key=lambda payload: (
                float(payload["metrics"]["sharpe"]),
                -float(payload["metrics"]["max_drawdown"]),
                float(payload["metrics"]["excess_return"]),
            ),
            reverse=True,
        )
        return [str(payload["run_id"]) for payload in sorted_payloads[: min(count, len(sorted_payloads))]]

    @staticmethod
    def _review(comparisons: list[EvidenceReport]) -> dict[str, Any]:
        if not comparisons:
            return {
                "return_delta": 0.0,
                "drawdown_delta": 0.0,
                "sample_sufficient": False,
                "overfit_risk": "unknown",
                "best_candidate_id": None,
            }
        best = max(
            comparisons,
            key=lambda report: report.comparison.objective_score if report.comparison is not None else -999.0,
        )
        comparison = best.comparison
        if comparison is None:
            return {
                "return_delta": 0.0,
                "drawdown_delta": 0.0,
                "sample_sufficient": False,
                "overfit_risk": "unknown",
                "best_candidate_id": best.candidate_run_id,
            }
        sample_count = float(comparison.provenance.get("sample_count") or 0)
        return_delta = comparison.business_metric_diffs.get("total_return", 0.0)
        drawdown_delta = comparison.business_metric_diffs.get("max_drawdown", 0.0)
        sharpe_delta = comparison.business_metric_diffs.get("sharpe", 0.0)
        overfit_risk = "medium"
        if sample_count >= 500 and sharpe_delta > 0 and drawdown_delta <= 0:
            overfit_risk = "low"
        if return_delta > 0.12 or sample_count < 252:
            overfit_risk = "high"
        return {
            "best_candidate_id": best.candidate_run_id,
            "return_delta": return_delta,
            "drawdown_delta": drawdown_delta,
            "sharpe_delta": sharpe_delta,
            "sample_count": sample_count,
            "sample_sufficient": sample_count >= 252,
            "overfit_risk": overfit_risk,
            "guardrail_violations": comparison.guardrail_violations,
            "objective_score": comparison.objective_score,
        }

    @staticmethod
    def _paper_trade_recommendation(review: dict[str, Any], system_findings: list[str]) -> str:
        if review.get("guardrail_violations"):
            return "reject"
        if not review.get("sample_sufficient"):
            return "continue_shadow"
        if review.get("overfit_risk") == "high":
            return "continue_shadow"
        if len(system_findings) > 4:
            return "continue_shadow"
        if float(review.get("objective_score") or 0.0) > 0:
            return "enter_paper"
        return "continue_shadow"

    @staticmethod
    def _system_findings() -> list[str]:
        return [
            "broker node is intentionally marked black_box; paper trading needs clearer execution trace",
            "transaction_cost_bps is fixed at 8; sensitivity analysis is still required",
            "historical fixture covers two years; out-of-sample split should be added before live use",
        ]

    def _stored_candidate_payloads(self, candidate_ids: list[str]) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for candidate_id in candidate_ids:
            stored = self.service.store.get_run(candidate_id)
            if stored is not None:
                payloads.append(stored.run.model_dump(mode="json"))
        return payloads

    @staticmethod
    def _chart_payload(
        baseline_run_id: str,
        candidate_payloads: list[dict[str, Any]],
        comparisons: list[EvidenceReport],
    ) -> dict[str, Any]:
        compared = {report.candidate_run_id: report for report in comparisons}
        candidates: list[dict[str, Any]] = []
        for payload in candidate_payloads:
            metrics = payload.get("metrics", {})
            if not isinstance(metrics, dict):
                continue
            max_drawdown = float(metrics.get("max_drawdown", 0.0))
            sharpe = float(metrics.get("sharpe", 0.0))
            guardrail_status = "violated" if max_drawdown > 0.2 else "ok"
            candidate_quality = "weak" if sharpe < 0.7 or guardrail_status == "violated" else "candidate"
            report = compared.get(str(payload.get("run_id")))
            objective_score = None
            if report is not None and report.comparison is not None:
                objective_score = report.comparison.objective_score
            candidates.append(
                {
                    "run_id": str(payload.get("run_id")),
                    "total_return": float(metrics.get("total_return", 0.0)),
                    "sharpe": sharpe,
                    "max_drawdown": max_drawdown,
                    "win_rate": float(metrics.get("win_rate", 0.0)),
                    "turnover": float(metrics.get("turnover", 0.0)),
                    "objective_score": objective_score,
                    "guardrail_status": guardrail_status,
                    "candidate_quality": candidate_quality,
                }
            )
        return {
            "baseline_run_id": baseline_run_id,
            "candidates": candidates,
            "chart_fields": ["total_return", "sharpe", "max_drawdown", "objective_score"],
        }

    @staticmethod
    def _guardrail_summary(candidates: list[dict[str, Any]]) -> str:
        violations = [str(item["run_id"]) for item in candidates if item.get("guardrail_status") == "violated"]
        if not violations:
            return "No candidate violated max_drawdown guardrail."
        return f"{len(violations)} candidates violated guardrails: {', '.join(violations[:5])}."
