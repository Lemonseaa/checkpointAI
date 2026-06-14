"""CLI handlers for external workflow evidence commands."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from loop_harness.evidence.quant_drill import QuantDrillRunner
from loop_harness.evidence.review_package import EvidenceReviewPackage
from loop_harness.harness import EvidenceHarness
from loop_harness.quant_data.batch import AShareBatchQuantRunner, AShareParameterGrid
from loop_harness.quant_data.manifest import AShareSampleManifest
from loop_harness.quant_data.models import AShareMarketDataSet
from loop_harness.quant_data.pipeline import AShareQuantLoopPipeline
from loop_harness.quant_data.platform_export import (
    JoinQuantBatchExportImporter,
    JoinQuantExportAdapter,
    QuantPlatformExport,
    evaluate_joinquant_export_quality,
)
from loop_harness.quant_data.providers import (
    AShareStaticProvider,
    MarketDataProvider,
    TushareDailyProvider,
    VendorCSVAShareProvider,
)
from loop_harness.quant_data.strategy_proposal import StrategyProposal, proposal_to_backtest_config


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

    package_parser = evidence_subparsers.add_parser("package")
    package_parser.add_argument("--baseline", required=True, dest="baseline_run_id")
    package_parser.add_argument("--candidate", dest="candidate_run_ids", action="append", default=[])
    package_parser.add_argument("--markdown", action="store_true")

    replay_package_parser = evidence_subparsers.add_parser("replay-package")
    replay_package_parser.add_argument("--path", required=True)

    package_submit_parser = evidence_subparsers.add_parser("package-submit")
    package_submit_parser.add_argument("--path", required=True)
    package_submit_parser.add_argument("--reason", required=True)

    package_decide_parser = evidence_subparsers.add_parser("package-decide")
    package_decide_parser.add_argument("--id", required=True, dest="decision_id")
    decision_group = package_decide_parser.add_mutually_exclusive_group(required=True)
    decision_group.add_argument("--approve", action="store_true")
    decision_group.add_argument("--reject", action="store_true")
    package_decide_parser.add_argument("--comment", required=True)

    package_decisions_parser = evidence_subparsers.add_parser("package-decisions")
    package_decisions_parser.add_argument("--scenario", dest="scenario_id")
    package_decisions_parser.add_argument("--status")

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

    quant_a_share_parser = evidence_subparsers.add_parser("quant-a-share-loop")
    quant_a_share_parser.add_argument("--symbol", required=True, dest="ts_code")
    quant_a_share_parser.add_argument(
        "--provider",
        choices=["static-a-share", "vendor-csv", "tushare"],
        default="static-a-share",
    )
    quant_a_share_parser.add_argument("--data-path")
    quant_a_share_parser.add_argument("--vendor", default="operator_export")
    quant_a_share_parser.add_argument("--tushare-token")
    quant_a_share_parser.add_argument("--start", required=True)
    quant_a_share_parser.add_argument("--end", required=True)
    quant_a_share_parser.add_argument("--adjusted", default="qfq", dest="adjusted_mode")
    quant_a_share_parser.add_argument("--fast-window", type=int, default=5)
    quant_a_share_parser.add_argument("--slow-window", type=int, default=20)
    quant_a_share_parser.add_argument("--scenario", default="quant_a_share", dest="scenario_id")
    quant_a_share_parser.add_argument("--kind", default="historical", dest="run_kind")

    quant_a_share_batch_parser = evidence_subparsers.add_parser("quant-a-share-batch")
    quant_a_share_batch_parser.add_argument("--manifest", required=True)
    quant_a_share_batch_parser.add_argument("--fast-windows", default="5,10,20")
    quant_a_share_batch_parser.add_argument("--slow-windows", default="20,60,120")
    quant_a_share_batch_parser.add_argument("--scenario", default="quant_a_share", dest="scenario_id")
    quant_a_share_batch_parser.add_argument("--kind", default="historical", dest="run_kind")

    joinquant_validate_parser = evidence_subparsers.add_parser("joinquant-validate")
    joinquant_validate_parser.add_argument("--export-dir", required=True)

    joinquant_import_parser = evidence_subparsers.add_parser("joinquant-import")
    joinquant_import_parser.add_argument("--export-dir", required=True)
    joinquant_import_parser.add_argument("--workflow", required=True, dest="workflow_id")
    joinquant_import_parser.add_argument("--scenario", default="quant_a_share", dest="scenario_id")

    joinquant_batch_parser = evidence_subparsers.add_parser("joinquant-batch")
    joinquant_batch_parser.add_argument("--batch-dir", required=True)
    joinquant_batch_parser.add_argument("--workflow", required=True, dest="workflow_id")
    joinquant_batch_parser.add_argument("--scenario", default="quant_a_share", dest="scenario_id")

    strategy_config_parser = evidence_subparsers.add_parser("strategy-proposal-to-config")
    strategy_config_parser.add_argument("--path", required=True)
    strategy_config_parser.add_argument("--platform", required=True, choices=["joinquant", "rqalpha"])


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

    if args.evidence_command == "package":
        try:
            package = harness.review_package_for_runs(args.baseline_run_id, args.candidate_run_ids)
        except ValueError as exc:
            print(str(exc))
            return 1
        if args.markdown:
            print(package.markdown)
        else:
            _print_json(package.model_dump(mode="json"))
        return 0

    if args.evidence_command == "replay-package":
        try:
            package = EvidenceReviewPackage.model_validate_json(Path(args.path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(str(exc))
            return 1
        validation_result = harness.validate_review_package(package)
        _print_json(validation_result.model_dump(mode="json"))
        return 0

    if args.evidence_command == "package-submit":
        try:
            package = EvidenceReviewPackage.model_validate_json(Path(args.path).read_text(encoding="utf-8"))
            decision = harness.submit_review_package(package, args.reason)
        except (OSError, ValueError) as exc:
            print(str(exc))
            return 1
        _print_json(decision.model_dump(mode="json"))
        return 0

    if args.evidence_command == "package-decide":
        try:
            if args.approve:
                decision = harness.approve_review_package(args.decision_id, args.comment)
            else:
                decision = harness.reject_review_package(args.decision_id, args.comment)
        except ValueError as exc:
            print(str(exc))
            return 1
        _print_json(decision.model_dump(mode="json"))
        return 0

    if args.evidence_command == "package-decisions":
        try:
            decisions = harness.list_review_package_decisions(
                scenario_id=args.scenario_id,
                status=args.status,
            )
        except ValueError as exc:
            print(str(exc))
            return 1
        _print_json([decision.model_dump(mode="json") for decision in decisions])
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

    if args.evidence_command == "quant-a-share-loop":
        try:
            dataset = _a_share_dataset_from_args(args)
            workflow_id = f"a_share_quant_{args.ts_code.replace('.', '_')}"
            loop_result = AShareQuantLoopPipeline(harness).run(
                dataset,
                workflow_id=workflow_id,
                scenario_id=args.scenario_id,
                run_kind=args.run_kind,
                fast_window=args.fast_window,
                slow_window=args.slow_window,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            print(str(exc))
            return 1
        _print_json(
            {
                "workflow_id": loop_result.workflow_id,
                "scenario_id": loop_result.scenario_id,
                "baseline_run_id": loop_result.baseline_run_id,
                "candidate_run_id": loop_result.candidate_run_id,
                "data_quality": loop_result.data_quality.model_dump(mode="json"),
                "recommendation": loop_result.comparison.recommendation.value,
                "summary": loop_result.comparison.summary,
                "chart": loop_result.chart.model_dump(mode="json"),
            }
        )
        return 0

    if args.evidence_command == "quant-a-share-batch":
        try:
            manifest = AShareSampleManifest.load(args.manifest)
            grid = AShareParameterGrid(
                fast_windows=_parse_int_list(args.fast_windows),
                slow_windows=_parse_int_list(args.slow_windows),
            )
            batch_result = AShareBatchQuantRunner(harness).run_grid(
                manifest,
                grid=grid,
                scenario_id=args.scenario_id,
                run_kind=args.run_kind,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            print(str(exc))
            return 1
        _print_json(batch_result.model_dump(mode="json"))
        return 0

    if args.evidence_command == "joinquant-validate":
        try:
            export = QuantPlatformExport.load(args.export_dir)
            quality = evaluate_joinquant_export_quality(export)
        except (OSError, ValueError, RuntimeError) as exc:
            print(str(exc))
            return 1
        _print_json(
            {
                "run_id": export.metadata.run_id,
                "platform": export.metadata.platform,
                "strategy_name": export.metadata.strategy_name,
                "export_dir": str(export.export_dir),
                "quality": quality.model_dump(mode="json"),
                "metrics": export.metrics,
            }
        )
        return 0

    if args.evidence_command == "joinquant-import":
        try:
            payload = JoinQuantExportAdapter().to_payload(
                args.export_dir,
                workflow_id=args.workflow_id,
                scenario_id=args.scenario_id,
            )
            result = harness.ingest_payload(payload)
            quality = evaluate_joinquant_export_quality(QuantPlatformExport.load(args.export_dir))
        except (OSError, ValueError, RuntimeError) as exc:
            print(str(exc))
            return 1
        _print_json(
            {
                "run_id": result.run.run_id,
                "workflow_id": result.run.workflow_id,
                "scenario_id": result.run.scenario_id,
                "recommendation": result.report.recommendation.value,
                "summary": result.report.summary,
                "quality": quality.model_dump(mode="json"),
            }
        )
        return 0

    if args.evidence_command == "joinquant-batch":
        try:
            joinquant_batch_result = JoinQuantBatchExportImporter(harness).import_batch(
                args.batch_dir,
                workflow_id=args.workflow_id,
                scenario_id=args.scenario_id,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            print(str(exc))
            return 1
        _print_json(joinquant_batch_result.model_dump(mode="json"))
        return 0

    if args.evidence_command == "strategy-proposal-to-config":
        try:
            proposal = StrategyProposal.model_validate_json(Path(args.path).read_text(encoding="utf-8"))
            config = proposal_to_backtest_config(proposal, platform=args.platform)
        except (OSError, ValueError, RuntimeError) as exc:
            print(str(exc))
            return 1
        _print_json(config.model_dump(mode="json"))
        return 0

    print("Unknown evidence command")
    return 1


def _parse_int_list(raw: str) -> list[int]:
    values = [int(value.strip()) for value in raw.split(",") if value.strip()]
    if not values:
        raise ValueError("integer list cannot be empty")
    return values


def _a_share_dataset_from_args(args: argparse.Namespace) -> AShareMarketDataSet:
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    provider: MarketDataProvider
    if args.provider == "static-a-share":
        provider = AShareStaticProvider()
    elif args.provider == "vendor-csv":
        if not args.data_path:
            raise ValueError("vendor-csv provider requires --data-path")
        provider = VendorCSVAShareProvider(args.data_path, vendor=args.vendor)
    elif args.provider == "tushare":
        if not args.tushare_token:
            raise ValueError("tushare provider requires --tushare-token")
        provider = TushareDailyProvider(args.tushare_token)
    else:
        raise ValueError(f"Unsupported A-share provider: {args.provider}")
    return provider.fetch(
        ts_code=args.ts_code,
        start=start,
        end=end,
        adjusted_mode=args.adjusted_mode,
    )


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
