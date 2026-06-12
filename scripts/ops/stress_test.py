"""Run a lightweight Loop Harness stress test."""

from __future__ import annotations

import argparse
import asyncio
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


async def _run_workflow(loop_harness: LoopHarness, index: int) -> str:
    """Run one workflow and return state."""

    run = await loop_harness.run(f"stress-{index}", [TaskSpec(description=f"task-{index}")])
    return run.state.value


async def _main(runs: int, concurrency: int) -> int:
    """Execute concurrent workflow runs."""

    with TemporaryDirectory() as tmp:
        loop_harness = LoopHarness(sqlite_path=Path(tmp) / "loop_harness.db")
        started_at = time.perf_counter()
        states: list[str] = []
        for offset in range(0, runs, concurrency):
            batch = range(offset, min(offset + concurrency, runs))
            states.extend(await asyncio.gather(*[_run_workflow(loop_harness, index) for index in batch]))
        elapsed = time.perf_counter() - started_at
    failures = sum(1 for state in states if state != "succeeded")
    print(
        "stress_summary "
        f"runs={runs} concurrency={concurrency} failures={failures} elapsed_seconds={elapsed:.6f}",
        flush=True,
    )
    return 0 if failures == 0 else 1


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args and run stress test."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args(argv)
    if args.runs <= 0 or args.concurrency <= 0:
        raise ValueError("--runs and --concurrency must be greater than zero")
    return asyncio.run(_main(args.runs, args.concurrency))


if __name__ == "__main__":
    raise SystemExit(main())
