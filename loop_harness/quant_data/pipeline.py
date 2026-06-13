"""A-share quant loop pipeline that emits Loop Harness evidence."""

from __future__ import annotations

from pydantic import BaseModel

from loop_harness.evidence.charts import OptimizationChartPayload
from loop_harness.evidence.models import EvidenceReport
from loop_harness.harness import EvidenceHarness
from loop_harness.quant_data.backtest import AShareBacktester, AShareBacktestResult
from loop_harness.quant_data.models import AShareMarketDataSet, MarketDataQualityReport


class AShareQuantLoopResult(BaseModel):
    """End-to-end A-share quant evidence loop result."""

    workflow_id: str
    scenario_id: str
    baseline_run_id: str
    candidate_run_id: str
    data_quality: MarketDataQualityReport
    comparison: EvidenceReport
    chart: OptimizationChartPayload


class AShareQuantLoopPipeline:
    """Run baseline/candidate A-share backtests and store evidence."""

    def __init__(self, harness: EvidenceHarness) -> None:
        self.harness = harness
        self.backtester = AShareBacktester()

    def run(
        self,
        dataset: AShareMarketDataSet,
        *,
        workflow_id: str,
        scenario_id: str,
        run_kind: str,
        fast_window: int,
        slow_window: int,
    ) -> AShareQuantLoopResult:
        """Run buy-hold baseline and moving-average candidate through evidence."""

        quality = dataset.quality_report()
        effective_run_kind = run_kind if dataset.decision_grade else "fixture"
        baseline = self.backtester.buy_and_hold(dataset, run_id=f"{workflow_id}_baseline")
        candidate = self.backtester.moving_average_crossover(
            dataset,
            run_id=f"{workflow_id}_ma_{fast_window}_{slow_window}",
            fast_window=fast_window,
            slow_window=slow_window,
        )
        self.harness.ingest_payload(
            self._payload(
                dataset,
                baseline,
                workflow_id=workflow_id,
                scenario_id=scenario_id,
                run_kind=effective_run_kind,
                quality=quality,
                requested_run_kind=run_kind,
            )
        )
        self.harness.ingest_payload(
            self._payload(
                dataset,
                candidate,
                workflow_id=workflow_id,
                scenario_id=scenario_id,
                run_kind=effective_run_kind,
                quality=quality,
                requested_run_kind=run_kind,
            )
        )
        comparison = self.harness.compare(baseline.run_id, candidate.run_id)
        chart = self.harness.optimization_chart_for_runs(baseline.run_id, [candidate.run_id])
        return AShareQuantLoopResult(
            workflow_id=workflow_id,
            scenario_id=scenario_id,
            baseline_run_id=baseline.run_id,
            candidate_run_id=candidate.run_id,
            data_quality=quality,
            comparison=comparison,
            chart=chart,
        )

    @staticmethod
    def _payload(
        dataset: AShareMarketDataSet,
        result: AShareBacktestResult,
        *,
        workflow_id: str,
        scenario_id: str,
        run_kind: str,
        quality: MarketDataQualityReport,
        requested_run_kind: str,
    ) -> dict[str, object]:
        metrics = result.metrics.model_dump()
        config = {"strategy": result.strategy, **result.parameters}
        metadata = {
            "market": "A_SHARE",
            "ts_code": dataset.ts_code,
            "name": dataset.name,
            "source": dataset.source,
            "vendor": dataset.vendor,
            "license_note": dataset.license_note,
            "adjusted_mode": dataset.adjusted_mode,
            "requested_run_kind": requested_run_kind,
            "start_date": dataset.start_date.isoformat() if dataset.start_date else None,
            "end_date": dataset.end_date.isoformat() if dataset.end_date else None,
            "data_quality": quality.model_dump(mode="json"),
        }
        return {
            "workflow_id": workflow_id,
            "run_id": result.run_id,
            "scenario_id": scenario_id,
            "run_kind": run_kind,
            "nodes": [
                {"id": "load_market_data", "name": "Load A-share market data", "type": "data"},
                {"id": "run_strategy", "name": f"Run {result.strategy}", "type": "strategy"},
                {"id": "evaluate_risk", "name": "Evaluate quant risk metrics", "type": "evaluation"},
                {"id": "build_report", "name": "Build evidence report", "type": "output"},
            ],
            "edges": [
                {"source": "load_market_data", "target": "run_strategy"},
                {"source": "run_strategy", "target": "evaluate_risk"},
                {"source": "evaluate_risk", "target": "build_report"},
            ],
            "trace": [
                {
                    "node_id": "load_market_data",
                    "status": "succeeded",
                    "duration_ms": 20,
                    "metrics": {"sample_count": float(result.metrics.sample_count)},
                    "output_summary": (
                        f"{dataset.ts_code} {dataset.start_date}..{dataset.end_date} "
                        f"source={dataset.source} adjusted={dataset.adjusted_mode}"
                    ),
                    "metadata": metadata,
                },
                {
                    "node_id": "run_strategy",
                    "status": "succeeded",
                    "duration_ms": 80,
                    "metrics": {"trade_count": float(result.metrics.trade_count), "turnover": result.metrics.turnover},
                    "output_summary": f"strategy={result.strategy}, parameters={result.parameters}",
                },
                {
                    "node_id": "evaluate_risk",
                    "status": "succeeded",
                    "duration_ms": 30,
                    "metrics": {
                        "sharpe": result.metrics.sharpe,
                        "max_drawdown": result.metrics.max_drawdown,
                        "win_rate": result.metrics.win_rate,
                    },
                },
                {"node_id": "build_report", "status": "succeeded", "duration_ms": 10},
            ],
            "metrics": metrics,
            "metric_schema": _metric_schema(),
            "config": config,
            "artifacts": [],
            "metadata": metadata,
        }


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
