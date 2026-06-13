"""Convert a TradingAgents-like export into Loop Harness evidence JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").exists() and (parent / "loop_harness").is_dir()
)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loop_harness.evidence.tradingagents import convert_tradingagents_export  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    """Parse args and write one Workflow Contract v1 payload."""

    parser = argparse.ArgumentParser(description="Convert TradingAgents export to Loop Harness evidence JSON.")
    parser.add_argument("--input", required=True, help="TradingAgents-like JSON export path.")
    parser.add_argument("--output", required=True, help="Output Workflow Contract v1 JSON path.")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    output_path = Path(args.output)
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("TradingAgents export must be a JSON object.")
    payload = convert_tradingagents_export(raw)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"converted_tradingagents_export input={input_path} output={output_path} run_id={payload['run_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
