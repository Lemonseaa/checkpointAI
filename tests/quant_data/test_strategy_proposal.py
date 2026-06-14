"""Tests for quant strategy proposal contracts."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from loop_harness.cli import main
from loop_harness.quant_data.strategy_proposal import (
    QuantStrategyType,
    StrategyProposal,
    proposal_to_backtest_config,
)


def test_strategy_proposal_requires_reason_and_expected_metric() -> None:
    with pytest.raises(ValidationError):
        StrategyProposal(
            scenario_id="quant_a_share",
            hypothesis="Shorter moving averages should react faster.",
            strategy_type=QuantStrategyType.MOVING_AVERAGE_CROSSOVER,
            universe=["600519.SH"],
            parameters={"fast_window": 5, "slow_window": 20},
            reason="",
            expected_metric="sharpe",
        )

    with pytest.raises(ValidationError):
        StrategyProposal(
            scenario_id="quant_a_share",
            hypothesis="Shorter moving averages should react faster.",
            strategy_type=QuantStrategyType.MOVING_AVERAGE_CROSSOVER,
            universe=["600519.SH"],
            parameters={"fast_window": 5, "slow_window": 20},
            reason="Test a faster crossover.",
            expected_metric="",
        )


def test_moving_average_proposal_validates_window_order() -> None:
    with pytest.raises(ValidationError, match="fast_window must be smaller than slow_window"):
        StrategyProposal(
            scenario_id="quant_a_share",
            hypothesis="Bad windows should be rejected.",
            strategy_type=QuantStrategyType.MOVING_AVERAGE_CROSSOVER,
            universe=["600519.SH"],
            parameters={"fast_window": 20, "slow_window": 5},
            reason="Guard against impossible moving average proposals.",
            expected_metric="sharpe",
        )


def test_strategy_proposal_converts_to_joinquant_config() -> None:
    proposal = StrategyProposal(
        scenario_id="quant_a_share",
        hypothesis="A 5/20 crossover may improve trend capture versus buy and hold.",
        strategy_type=QuantStrategyType.MOVING_AVERAGE_CROSSOVER,
        universe=["600519.SH", "510300.SH"],
        parameters={"fast_window": 5, "slow_window": 20},
        reason="Historical samples show shorter trend windows deserve a controlled test.",
        expected_metric="sharpe",
    )

    config = proposal_to_backtest_config(proposal, platform="joinquant")

    assert config.platform == "joinquant"
    assert config.strategy_type == "moving_average_crossover"
    assert config.parameters["fast_window"] == 5
    assert config.parameters["slow_window"] == 20
    assert config.universe == ["600519.SH", "510300.SH"]
    assert config.run_kind == "historical"
    assert "export results using the Quant Platform Export Contract" in config.notes


def test_strategy_proposal_converts_to_rqalpha_config() -> None:
    proposal = StrategyProposal(
        scenario_id="quant_a_share",
        hypothesis="A 20-day momentum ranking may filter weak trend names.",
        strategy_type=QuantStrategyType.MOMENTUM,
        universe=["510300.SH"],
        parameters={"lookback_window": 20, "top_n": 1},
        reason="Momentum is a simple challenger strategy for A-share index samples.",
        expected_metric="excess_return",
    )

    config = proposal_to_backtest_config(proposal, platform="rqalpha")

    assert config.platform == "rqalpha"
    assert config.parameters["lookback_window"] == 20
    assert config.metadata["source_proposal_id"] == proposal.id


def test_unknown_backtest_platform_is_rejected() -> None:
    proposal = StrategyProposal(
        scenario_id="quant_a_share",
        hypothesis="A 5/20 crossover may improve trend capture versus buy and hold.",
        strategy_type=QuantStrategyType.MOVING_AVERAGE_CROSSOVER,
        universe=["600519.SH"],
        parameters={"fast_window": 5, "slow_window": 20},
        reason="Historical samples show shorter trend windows deserve a controlled test.",
        expected_metric="sharpe",
    )

    with pytest.raises(ValueError, match="Unsupported quant backtest platform"):
        proposal_to_backtest_config(proposal, platform="unknown")


def test_strategy_proposal_to_config_cli_reads_json(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(
        json.dumps(
            {
                "scenario_id": "quant_a_share",
                "hypothesis": "A 5/20 crossover may improve trend capture versus buy and hold.",
                "strategy_type": "moving_average_crossover",
                "universe": ["600519.SH"],
                "parameters": {"fast_window": 5, "slow_window": 20},
                "reason": "Historical samples show shorter trend windows deserve a controlled test.",
                "expected_metric": "sharpe",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--db",
            str(tmp_path / "proposal.db"),
            "evidence",
            "strategy-proposal-to-config",
            "--path",
            str(proposal_path),
            "--platform",
            "joinquant",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["platform"] == "joinquant"
    assert payload["strategy_type"] == "moving_average_crossover"
    assert payload["parameters"]["fast_window"] == 5
    assert payload["metadata"]["source_proposal_id"]


def test_strategy_proposal_to_config_cli_reads_batch_json(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    proposal_path = tmp_path / "proposals.json"
    proposal_path.write_text(
        json.dumps(
            [
                {
                    "scenario_id": "quant_a_share",
                    "hypothesis": "A 5/20 crossover may improve trend capture.",
                    "strategy_type": "moving_average_crossover",
                    "universe": ["600519.SH"],
                    "parameters": {"fast_window": 5, "slow_window": 20},
                    "reason": "Test a faster trend filter.",
                    "expected_metric": "sharpe",
                },
                {
                    "scenario_id": "quant_a_share",
                    "hypothesis": "A 20-day momentum filter may reduce weak names.",
                    "strategy_type": "momentum",
                    "universe": ["510300.SH"],
                    "parameters": {"lookback_window": 20, "top_n": 1},
                    "reason": "Test simple momentum as a challenger.",
                    "expected_metric": "excess_return",
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--db",
            str(tmp_path / "proposal.db"),
            "evidence",
            "strategy-proposal-to-config",
            "--path",
            str(proposal_path),
            "--platform",
            "joinquant",
            "--batch",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 2
    assert [item["platform"] for item in payload["configs"]] == ["joinquant", "joinquant"]
    assert payload["configs"][1]["strategy_type"] == "momentum"
