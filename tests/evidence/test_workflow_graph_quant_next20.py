"""Workflow graph and quant drill v2 tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from loop_harness.evidence import EvidenceService, EvidenceStore
from loop_harness.evidence.graph import WorkflowGraphBuilder
from loop_harness.evidence.quant_contracts import QuantBacktestOutput, QuantRunInput
from loop_harness.evidence.quant_drill import QuantDrillRunner
from loop_harness.prompt import Proposal, ProposalKind, ProposalPatch, ProposalTargetType


def _graph_payload(run_id: str = "graph-run") -> dict[str, object]:
    return {
        "workflow_id": "graph_quant_flow",
        "run_id": run_id,
        "scenario_id": "quant",
        "run_kind": "historical",
        "nodes": [
            {"id": "load_data", "name": "Load Data", "type": "data"},
            {"id": "researcher", "name": "Research Agent", "type": "agent", "metadata": {"optimizable": True}},
            {"id": "llm_vote", "name": "LLM Vote", "type": "llm"},
            {"id": "broker", "name": "Broker", "type": "external", "metadata": {"black_box": True}},
            {"id": "report", "name": "Report", "type": "output"},
        ],
        "edges": [
            {"source": "load_data", "target": "researcher"},
            {"source": "researcher", "target": "llm_vote"},
            {"source": "llm_vote", "target": "broker"},
            {"source": "broker", "target": "report"},
        ],
        "trace": [
            {"node_id": "load_data", "status": "succeeded", "duration_ms": 80, "metrics": {"sample_count": 504}},
            {
                "node_id": "researcher",
                "status": "succeeded",
                "duration_ms": 250,
                "cost": 0.05,
                "metrics": {"sharpe": 1.1},
                "input_summary": "bars",
                "output_summary": "signal candidate",
            },
            {"node_id": "llm_vote", "status": "succeeded", "duration_ms": 160, "cost": 0.03},
            {"node_id": "report", "status": "succeeded", "duration_ms": 50},
        ],
        "metrics": {"sharpe": 1.1, "max_drawdown": 0.12, "sample_count": 504, "latency_ms": 540},
        "metric_schema": {
            "sharpe": {"direction": "higher", "category": "business", "weight": 0.7},
            "max_drawdown": {"direction": "lower", "category": "guardrail", "weight": 0.3, "threshold": 0.2},
            "sample_count": {"direction": "higher", "category": "data_quality", "weight": 0.0},
            "latency_ms": {"direction": "lower", "category": "system", "weight": 0.0},
        },
        "config": {"fast_window": 8, "slow_window": 21, "risk_threshold": 0.12},
        "artifacts": [{"type": "html", "path": "reports/graph-run.html", "metadata": {"node_id": "report"}}],
    }


class WorkflowGraphQuantNext20Test(unittest.TestCase):
    """Validate graph payloads and richer quant drills."""

    def test_graph_payload_contains_layout_filters_metric_sources_and_gap_markers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = EvidenceService(EvidenceStore(Path(tmp) / "evidence.db"))
            service.ingest_payload(_graph_payload())

            graph = service.graph_for_run("graph-run")
            researcher = next(node for node in graph.nodes if node.id == "researcher")
            broker = next(node for node in graph.nodes if node.id == "broker")

            self.assertEqual(graph.workflow_id, "graph_quant_flow")
            self.assertEqual(graph.run_id, "graph-run")
            self.assertEqual(graph.filters["black_box"], ["broker"])
            self.assertIn("sharpe", graph.metric_sources)
            self.assertEqual(graph.metric_sources["sharpe"], ["researcher"])
            self.assertEqual(researcher.node_type, "agent")
            self.assertEqual(researcher.layout["x"], 1)
            self.assertTrue(researcher.optimizable)
            self.assertIn("sharpe", researcher.metric_names)
            self.assertTrue(broker.black_box)
            self.assertTrue(any(gap.code == "node.black_box" for gap in broker.gaps))

    def test_api_graph_and_proposal_targeting_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = EvidenceService(EvidenceStore(Path(tmp) / "evidence.db"))
            service.ingest_payload(_graph_payload())
            graph = WorkflowGraphBuilder().build(service.store.get_run("graph-run"))  # type: ignore[arg-type]

            proposal = Proposal(
                scenario_id="quant",
                proposal_kind=ProposalKind.PARAMETER,
                target_type=ProposalTargetType.ADAPTER_CONFIG,
                target_id="researcher.fast_window",
                patch=ProposalPatch(operation="replace", before=8, after=10),
                reason="Researcher node produced Sharpe; small fast_window change should be shadowed.",
                expected_metric="sharpe",
                metadata=graph.proposal_target_metadata("researcher", "fast_window", "sharpe"),
            )

            self.assertEqual(proposal.metadata["target_node_id"], "researcher")
            self.assertEqual(proposal.metadata["target_config_surface"], "fast_window")
            self.assertEqual(proposal.metadata["expected_metric"], "sharpe")
            self.assertEqual(proposal.metadata["target_node_type"], "agent")

    def test_quant_contracts_and_v2_drill_include_chart_payload_and_weak_candidates(self) -> None:
        run_input = QuantRunInput(
            capital=100000,
            universe=["AAPL", "MSFT"],
            start_date="2024-01-01",
            end_date="2025-12-31",
            frequency="1d",
            risk_limits={"max_drawdown": 0.2},
            objective_metric="sharpe",
        )
        output = QuantBacktestOutput(
            total_return=0.21,
            annual_return=0.105,
            sharpe=1.2,
            max_drawdown=0.12,
            volatility=0.18,
            win_rate=0.55,
            turnover=1.7,
            trade_count=88,
            benchmark_return=0.14,
            excess_return=0.07,
        )

        with tempfile.TemporaryDirectory() as tmp:
            service = EvidenceService(EvidenceStore(Path(tmp) / "evidence.db"))
            result = QuantDrillRunner(service).run_v2(candidate_count=12, comparison_count=4)
            weak_graph = service.graph_for_run("quant_candidate_drill_weak")

            self.assertEqual(run_input.objective_metric, "sharpe")
            self.assertGreater(output.excess_return, 0)
            self.assertEqual(result.run_count, 13)
            self.assertEqual(weak_graph.scenario_id, "quant")
            self.assertEqual(len(result.chart_payload["candidates"]), 12)
            self.assertTrue(any(item["guardrail_status"] == "violated" for item in result.chart_payload["candidates"]))
            self.assertTrue(any(item["candidate_quality"] == "weak" for item in result.chart_payload["candidates"]))
            self.assertIn("guardrail_summary", result.review)


if __name__ == "__main__":
    unittest.main()
