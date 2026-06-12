"""CLI handlers for external workflow evidence commands."""

from __future__ import annotations

import argparse
import json
from typing import Any

from loop_harness.evidence.quant_drill import QuantDrillRunner
from loop_harness.harness import EvidenceHarness


def register_evidence_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register evidence subcommands."""

    evidence_parser = subparsers.add_parser("evidence")
    evidence_subparsers = evidence_parser.add_subparsers(dest="evidence_command")

    ingest_parser = evidence_subparsers.add_parser("ingest")
    ingest_parser.add_argument("path")

    visualize_parser = evidence_subparsers.add_parser("visualize")
    visualize_parser.add_argument("--run", required=True, dest="run_id")

    map_parser = evidence_subparsers.add_parser("map")
    map_parser.add_argument("--workflow", required=True, dest="workflow_id")

    graph_parser = evidence_subparsers.add_parser("graph")
    graph_parser.add_argument("--run", dest="run_id")
    graph_parser.add_argument("--workflow", dest="workflow_id")

    chart_parser = evidence_subparsers.add_parser("chart")
    chart_parser.add_argument("--workflow", dest="workflow_id")
    chart_parser.add_argument("--baseline", dest="baseline_run_id")
    chart_parser.add_argument("--candidate", dest="candidate_run_ids", action="append", default=[])

    import_quant_csv_parser = evidence_subparsers.add_parser("import-quant-csv")
    import_quant_csv_parser.add_argument("--path", required=True)
    import_quant_csv_parser.add_argument("--workflow", required=True, dest="workflow_id")
    import_quant_csv_parser.add_argument("--scenario", default="quant", dest="scenario_id")
    import_quant_csv_parser.add_argument("--kind", default="historical", dest="run_kind")

    gaps_parser = evidence_subparsers.add_parser("gaps")
    gaps_parser.add_argument("--run", required=True, dest="run_id")

    node_parser = evidence_subparsers.add_parser("node")
    node_parser.add_argument("--run", required=True, dest="run_id")
    node_parser.add_argument("--node", required=True, dest="node_id")

    compare_parser = evidence_subparsers.add_parser("compare")
    compare_parser.add_argument("--baseline", required=True)
    compare_parser.add_argument("--candidate", required=True)

    export_parser = evidence_subparsers.add_parser("export")
    export_parser.add_argument("--baseline", required=True)
    export_parser.add_argument("--candidate", required=True)

    report_parser = evidence_subparsers.add_parser("report")
    report_parser.add_argument("--run", dest="run_id")
    report_parser.add_argument("--baseline")
    report_parser.add_argument("--candidate")

    quant_drill_parser = evidence_subparsers.add_parser("quant-drill")
    quant_drill_parser.add_argument("--candidates", type=int, default=30)
    quant_drill_parser.add_argument("--comparisons", type=int, default=5)
    quant_drill_parser.add_argument("--v2", action="store_true")


def handle_evidence_command(args: argparse.Namespace, db_path: str) -> int:
    """Handle evidence CLI subcommands."""

    harness = EvidenceHarness(db_path)

    if args.evidence_command == "ingest":
        result = harness.ingest_file(args.path)
        _print_json(
            {
                "run_id": result.run.run_id,
                "workflow_id": result.run.workflow_id,
                "trace_coverage": result.visualization.trace_coverage,
                "metric_coverage": result.visualization.metric_coverage,
                "black_box_node_ids": result.visualization.black_box_node_ids,
                "recommendation": result.report.recommendation.value,
                "summary": result.report.summary,
            }
        )
        return 0

    if args.evidence_command == "visualize":
        try:
            visualization = harness.visualize(args.run_id)
        except ValueError:
            print(f"Unknown run: {args.run_id}")
            return 1
        _print_json(visualization.model_dump(mode="json"))
        return 0

    if args.evidence_command == "map":
        try:
            workflow_map = harness.workflow_map(args.workflow_id)
        except ValueError:
            print(f"Unknown workflow: {args.workflow_id}")
            return 1
        _print_json(workflow_map.model_dump(mode="json"))
        return 0

    if args.evidence_command == "graph":
        try:
            if args.run_id:
                graph = harness.graph_for_run(args.run_id)
            elif args.workflow_id:
                graph = harness.graph_for_workflow(args.workflow_id)
            else:
                print("graph requires --run or --workflow")
                return 1
        except ValueError as exc:
            print(str(exc))
            return 1
        _print_json(graph.model_dump(mode="json"))
        return 0

    if args.evidence_command == "chart":
        try:
            if args.workflow_id:
                chart = harness.optimization_chart(args.workflow_id)
            elif args.baseline_run_id and args.candidate_run_ids:
                chart = harness.optimization_chart_for_runs(args.baseline_run_id, args.candidate_run_ids)
            else:
                print("chart requires --workflow or --baseline with at least one --candidate")
                return 1
        except ValueError as exc:
            print(str(exc))
            return 1
        _print_json(chart.model_dump(mode="json"))
        return 0

    if args.evidence_command == "import-quant-csv":
        try:
            import_result = harness.ingest_quant_csv(
                args.path,
                workflow_id=args.workflow_id,
                scenario_id=args.scenario_id,
                run_kind=args.run_kind,
            )
        except ValueError as exc:
            print(str(exc))
            return 1
        _print_json(import_result.model_dump(mode="json"))
        return 0

    if args.evidence_command == "gaps":
        try:
            gap_report = harness.gap_report(args.run_id)
        except ValueError:
            print(f"Unknown run: {args.run_id}")
            return 1
        _print_json(gap_report.model_dump(mode="json"))
        return 0

    if args.evidence_command == "node":
        try:
            detail = harness.node_detail(args.run_id, args.node_id)
        except ValueError as exc:
            print(str(exc))
            return 1
        _print_json(detail.model_dump(mode="json"))
        return 0

    if args.evidence_command == "compare":
        report = harness.compare(args.baseline, args.candidate)
        _print_json(report.model_dump(mode="json"))
        return 0

    if args.evidence_command == "export":
        print(harness.export_comparison_markdown(args.baseline, args.candidate))
        return 0

    if args.evidence_command == "report":
        if args.baseline and args.candidate:
            report = harness.compare(args.baseline, args.candidate)
            _print_json(report.model_dump(mode="json"))
            return 0
        if args.run_id:
            try:
                report = harness.report(args.run_id)
            except ValueError:
                print(f"Unknown run: {args.run_id}")
                return 1
            _print_json(report.model_dump(mode="json"))
            return 0
        print("report requires --run or --baseline and --candidate")
        return 1

    if args.evidence_command == "quant-drill":
        runner = QuantDrillRunner(harness.service)
        drill_result = runner.run_v2(
            candidate_count=args.candidates,
            comparison_count=args.comparisons,
        ) if args.v2 else runner.run(candidate_count=args.candidates, comparison_count=args.comparisons)
        _print_json(
            {
                "workflow_id": drill_result.workflow_id,
                "baseline_run_id": drill_result.baseline_run_id,
                "run_count": drill_result.run_count,
                "candidate_count": drill_result.candidate_count,
                "comparison_count": len(drill_result.comparisons),
                "compared_candidate_ids": [
                    report.candidate_run_id for report in drill_result.comparisons
                ],
                "report_count": drill_result.report_count,
                "system_findings": drill_result.system_findings,
                "paper_trade_recommendation": drill_result.paper_trade_recommendation,
                "review": drill_result.review,
                "chart_payload": drill_result.chart_payload,
                "summary": drill_result.summary,
            }
        )
        return 0

    print("Unknown evidence command")
    return 1


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
