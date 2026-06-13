"""Convert a TradingAgents-like export into Loop Harness evidence JSON."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").exists() and (parent / "loop_harness").is_dir()
)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loop_harness.evidence.quant_contracts import QuantEvidenceContractValidator  # noqa: E402
from loop_harness.evidence.tradingagents import convert_tradingagents_export  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    """Parse args and write Workflow Contract v1 payloads."""

    parser = argparse.ArgumentParser(description="Convert TradingAgents export to Loop Harness evidence JSON.")
    parser.add_argument("--input", help="TradingAgents-like JSON export path.")
    parser.add_argument("--output", help="Output Workflow Contract v1 JSON path.")
    parser.add_argument("--input-dir", help="Directory of TradingAgents-like JSON exports.")
    parser.add_argument("--output-dir", help="Directory for converted Workflow Contract v1 JSON files.")
    parser.add_argument("--strict", action="store_true", help="Return non-zero when any batch item fails.")
    args = parser.parse_args(argv)

    if args.input_dir or args.output_dir:
        if not args.input_dir or not args.output_dir:
            parser.error("--input-dir and --output-dir must be supplied together.")
        return _convert_directory(Path(args.input_dir), Path(args.output_dir), strict=bool(args.strict))
    if not args.input or not args.output:
        parser.error("--input and --output are required unless --input-dir/--output-dir are used.")
    input_path = Path(args.input)
    output_path = Path(args.output)
    payload = _convert_file(input_path, output_path)
    print(f"converted_tradingagents_export input={input_path} output={output_path} run_id={payload['run_id']}")
    return 0


def _convert_file(input_path: Path, output_path: Path) -> dict[str, object]:
    """Convert one export file and write one payload."""

    raw = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("TradingAgents export must be a JSON object.")
    payload = convert_tradingagents_export(raw)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _convert_directory(input_dir: Path, output_dir: Path, *, strict: bool) -> int:
    """Convert a directory and print a compact quality summary."""

    converted = 0
    failed = 0
    missing_metrics: Counter[str] = Counter()
    black_box_warnings = 0
    sample_counts: list[float] = []

    for input_path in sorted(input_dir.glob("*.json")):
        output_path = output_dir / input_path.name
        try:
            raw = json.loads(input_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("TradingAgents export must be a JSON object.")
            missing_metrics.update(_missing_required_metrics(raw))
            payload = convert_tradingagents_export(raw)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            converted += 1
            sample_count = payload.get("metrics", {}).get("sample_count") if isinstance(payload.get("metrics"), dict) else None
            if isinstance(sample_count, int | float):
                sample_counts.append(float(sample_count))
            if _has_black_box_warning(payload):
                black_box_warnings += 1
        except Exception as exc:
            failed += 1
            print(f"conversion_failed input={input_path} error={exc}")

    missing_summary = ",".join(f"{name}:{count}" for name, count in sorted(missing_metrics.items())) or "none"
    average_sample_count = round(sum(sample_counts) / len(sample_counts), 2) if sample_counts else 0.0
    print(
        "batch_summary "
        f"converted={converted} failed={failed} "
        f"missing_required_metrics={missing_summary} "
        f"black_box_trace_warnings={black_box_warnings} "
        f"average_sample_count={average_sample_count}"
    )
    return 1 if strict and failed else 0


def _missing_required_metrics(raw: dict[str, object]) -> list[str]:
    metrics = raw.get("metrics")
    if not isinstance(metrics, dict):
        return sorted(QuantEvidenceContractValidator.REQUIRED_METRICS)
    return sorted(metric for metric in QuantEvidenceContractValidator.REQUIRED_METRICS if metric not in metrics)


def _has_black_box_warning(payload: dict[str, object]) -> bool:
    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        return True
    return any(isinstance(node, dict) and node.get("metadata", {}).get("black_box") for node in nodes)


if __name__ == "__main__":
    raise SystemExit(main())
