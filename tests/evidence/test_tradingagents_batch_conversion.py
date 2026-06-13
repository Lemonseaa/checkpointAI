"""TradingAgents batch conversion tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "tradingagents_like_run.json"
ROOT = Path(__file__).resolve().parents[2]


class TradingAgentsBatchConversionTest(unittest.TestCase):
    """Validate batch conversion before real TradingAgents adapter work."""

    def test_batch_conversion_reports_failures_without_strict_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "output"
            input_dir.mkdir()
            good = json.loads(FIXTURE.read_text(encoding="utf-8"))
            bad = json.loads(FIXTURE.read_text(encoding="utf-8"))
            bad["metrics"].pop("max_drawdown")
            (input_dir / "good.json").write_text(json.dumps(good), encoding="utf-8")
            (input_dir / "bad.json").write_text(json.dumps(bad), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/business_lines/quant/convert_tradingagents_export.py",
                    "--input-dir",
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((output_dir / "good.json").exists())
            self.assertFalse((output_dir / "bad.json").exists())
            self.assertIn("converted=1", completed.stdout)
            self.assertIn("failed=1", completed.stdout)
            self.assertIn("missing_required_metrics=max_drawdown:1", completed.stdout)

    def test_batch_conversion_strict_returns_nonzero_on_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "output"
            input_dir.mkdir()
            bad = json.loads(FIXTURE.read_text(encoding="utf-8"))
            bad["metrics"].pop("sharpe")
            (input_dir / "bad.json").write_text(json.dumps(bad), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/business_lines/quant/convert_tradingagents_export.py",
                    "--input-dir",
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                    "--strict",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 1)
            self.assertIn("failed=1", completed.stdout)


if __name__ == "__main__":
    unittest.main()
