"""Run a lightweight Loop Harness health check."""

from __future__ import annotations

import asyncio
import sys
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


async def main() -> int:
    """Execute one in-memory workflow and print health state."""

    with TemporaryDirectory() as tmp:
        loop_harness = LoopHarness(sqlite_path=Path(tmp) / "loop_harness.db")
        run = await loop_harness.run("health", [TaskSpec(description="ping")])
        summary = loop_harness.metrics.get_summary()
    if run.state.value != "succeeded":
        print(f"unhealthy: run_state={run.state.value}")
        return 1
    print(f"healthy: run_state={run.state.value} task_success={summary['task_success']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
