"""Quant Evidence MVP contract, import, comparison, and package tests."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from loop_harness.evidence.quant_contracts import (
    QuantBacktestOutput,
    QuantEvidenceContractValidator,
)
from loop_harness.harness import EvidenceHarness


class QuantEvidenceMVPTest(unittest.TestCase):
    """Validate the first real quant evidence loop shape."""

    def test_quant_output_requires_core_metrics_and_sample_count(self) -> None:
        """Quant runs without enough metrics cannot become recommendation evidence."""

        with self.assertRaises(ValidationError):
            QuantBacktestOutput.model_validate(
                {
                    "total_return": 0.2,
                    "annual_return": 0.1,
                    "sharpe": 1.1,
                    "max_drawdown": 0.12,
                    "volatility": 0.18,
                    "win_rate": 0.55,
                    "turnover": 1.2,
                    "trade_count": 50,
                    "benchmark_return": 0.05,
                    "excess_return": 0.15,
                }
            )

        output = QuantBacktestOutput.model_validate(
            {
                "total_return": 0.2,
                "annual_return": 0.1,
                "sharpe": 1.1,
                "max_drawdown": 0.12,
                "volatility": 0.18,
                "win_rate": 0.55,
                "turnover": 1.2,
                "trade_count": 50,
                "benchmark_return": 0.05,
                "excess_return": 0.15,
                "sample_count": 252,
            }
        )

        self.assertEqual(output.sample_count, 252)

    def test_quant_contract_validator_rejects_missing_core_metrics(self) -> None:
        """Quant-specific evidence has a stricter contract than generic workflow evidence."""

        result = QuantEvidenceContractValidator().validate(
            {
                "workflow_id": "quant_mvp",
                "run_id": "candidate_missing_drawdown",
                "run_kind": "historical",
                "nodes": [{"id": "strategy"}],
                "trace": [{"node_id": "strategy", "metrics": {"sharpe": 1.2}}],
                "metrics": {"sharpe": 1.2, "total_return": 0.2, "sample_count": 252},
            }
        )

        self.assertFalse(result.accepted)
        self.assertIn("quant.metric_missing", {issue.code for issue in result.issues})
        self.assertIn("max_drawdown", {issue.field for issue in result.issues})

    def test_quant_csv_import_uses_real_sample_count_and_rejects_bad_drawdown(self) -> None:
        """CSV import should preserve sample_count and reject invalid quant values."""

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "quant.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "run_id",
                        "fast_window",
                        "slow_window",
                        "total_return",
                        "sharpe",
                        "max_drawdown",
                        "win_rate",
                        "turnover",
                        "trade_count",
                        "sample_count",
                        "capital",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "run_id": "baseline",
                        "fast_window": "8",
                        "slow_window": "21",
                        "total_return": "0.10",
                        "sharpe": "0.80",
                        "max_drawdown": "0.16",
                        "win_rate": "0.52",
                        "turnover": "1.2",
                        "trade_count": "80",
                        "sample_count": "252",
                        "capital": "100000",
                    }
                )
                writer.writerow(
                    {
                        "run_id": "candidate_bad",
                        "fast_window": "4",
                        "slow_window": "9",
                        "total_return": "0.40",
                        "sharpe": "1.40",
                        "max_drawdown": "1.40",
                        "win_rate": "0.60",
                        "turnover": "2.4",
                        "trade_count": "140",
                        "sample_count": "252",
                        "capital": "100000",
                    }
                )
            harness = EvidenceHarness(Path(tmp) / "evidence.db")

            with self.assertRaisesRegex(ValueError, "max_drawdown must be between 0 and 1"):
                harness.ingest_quant_csv(
                    csv_path,
                    workflow_id="quant_mvp",
                    scenario_id="quant",
                    run_kind="historical",
                )

            rows = csv_path.read_text(encoding="utf-8").replace("1.40,1.40", "1.40,0.24")
            csv_path.write_text(rows, encoding="utf-8")
            result = harness.ingest_quant_csv(
                csv_path,
                workflow_id="quant_mvp",
                scenario_id="quant",
                run_kind="historical",
            )

            self.assertEqual(result.imported_count, 2)
            candidate = harness.store.get_run("candidate_bad")
            self.assertIsNotNone(candidate)
            self.assertEqual(candidate.run.metrics["sample_count"], 252.0)  # type: ignore[union-attr]
            self.assertEqual(candidate.run.metadata["capital"], 100000.0)  # type: ignore[union-attr]

    def test_quant_comparison_blocks_paper_when_drawdown_worsens_past_guardrail(self) -> None:
        """High-return candidates with unacceptable drawdown should not be recommended."""

        with tempfile.TemporaryDirectory() as tmp:
            harness = EvidenceHarness(Path(tmp) / "evidence.db")
            csv_path = Path(tmp) / "quant.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "run_id,fast_window,slow_window,total_return,sharpe,max_drawdown,win_rate,turnover,trade_count,sample_count",
                        "baseline,8,21,0.10,0.80,0.12,0.52,1.2,80,252",
                        "candidate_risky,4,9,0.40,1.40,0.24,0.60,2.4,140,252",
                    ]
                ),
                encoding="utf-8",
            )
            harness.ingest_quant_csv(
                csv_path,
                workflow_id="quant_mvp",
                scenario_id="quant",
                run_kind="historical",
            )

            report = harness.compare("baseline", "candidate_risky")
            package = harness.review_package_for_runs("baseline", ["candidate_risky"])

        self.assertEqual(report.recommendation.value, "reject")
        self.assertIn("max_drawdown", report.comparison.guardrail_violations)  # type: ignore[union-attr]
        self.assertEqual(package.recommended_action, "reject_or_refine")
        self.assertIn("是否建议进入 paper trading：否", package.markdown)

    def test_quant_review_package_answers_paper_trading_questions(self) -> None:
        """A strong candidate package should answer the human paper-trading decision."""

        with tempfile.TemporaryDirectory() as tmp:
            harness = EvidenceHarness(Path(tmp) / "evidence.db")
            csv_path = Path(tmp) / "quant.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "run_id,fast_window,slow_window,total_return,sharpe,max_drawdown,win_rate,turnover,trade_count,sample_count",
                        "baseline,8,21,0.10,0.80,0.14,0.52,1.2,80,252",
                        "candidate_strong,10,24,0.24,1.25,0.11,0.58,1.1,90,252",
                    ]
                ),
                encoding="utf-8",
            )
            harness.ingest_quant_csv(
                csv_path,
                workflow_id="quant_mvp",
                scenario_id="quant",
                run_kind="historical",
            )

            package = harness.review_package_for_runs("baseline", ["candidate_strong"])

        self.assertEqual(package.recommended_action, "review_for_paper")
        self.assertIn("这次测试了什么策略", package.markdown)
        self.assertIn("baseline 是什么", package.markdown)
        self.assertIn("candidate 改了什么", package.markdown)
        self.assertIn("是否建议进入 paper trading：是", package.markdown)


if __name__ == "__main__":
    unittest.main()
