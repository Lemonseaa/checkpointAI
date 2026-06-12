"""Run a lightweight Loop Harness performance benchmark."""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").exists() and (parent / "loop_harness").is_dir()
)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loop_harness import LoopHarness  # noqa: E402
from loop_harness.models import TaskSpec  # noqa: E402


async def _run_once() -> float:
    """Run one small workflow and return duration."""

    with TemporaryDirectory() as tmp:
        loop_harness = LoopHarness(sqlite_path=Path(tmp) / "loop_harness.db")
        started_at = time.perf_counter()
        run = await loop_harness.run("benchmark", [TaskSpec(description="ping")])
        duration = time.perf_counter() - started_at
    if run.state.value != "succeeded":
        raise RuntimeError(f"benchmark run failed: {run.state.value}")
    return duration


async def _main(runs: int) -> int:
    """Run benchmark iterations."""

    durations = [await _run_once() for _ in range(runs)]
    print(
        "benchmark_summary "
        f"runs={runs} "
        f"avg_seconds={statistics.mean(durations):.6f} "
        f"max_seconds={max(durations):.6f}",
        flush=True,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args and run benchmark."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=20)
    args = parser.parse_args(argv)
    if args.runs <= 0:
        raise ValueError("--runs must be greater than zero")
    return asyncio.run(_main(args.runs))


if __name__ == "__main__":
    raise SystemExit(main())
