"""TradingAgents export-only spike conversion helpers."""

from __future__ import annotations

from typing import Any

from loop_harness.evidence.quant_contracts import QuantEvidenceContractValidator


def convert_tradingagents_export(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert a TradingAgents-like export into Workflow Contract v1."""

    agents = raw.get("agents")
    if not isinstance(agents, list) or not agents:
        raise ValueError("TradingAgents export requires a non-empty agents list.")
    metrics = _numeric_dict(raw.get("metrics"))
    payload = {
        "workflow_id": str(raw.get("workflow_id") or "tradingagents_quant_research"),
        "run_id": str(raw.get("run_id") or "tradingagents_run"),
        "scenario_id": str(raw.get("scenario_id") or "quant"),
        "run_kind": str(raw.get("run_kind") or "historical"),
        "nodes": [_node(agent) for agent in agents],
        "edges": _edges(agents),
        "trace": [_trace(agent) for agent in agents],
        "metrics": metrics,
        "metric_schema": _metric_schema(),
        "config": _config(raw),
        "artifacts": raw.get("artifacts") if isinstance(raw.get("artifacts"), list) else [],
        "metadata": {
            "source": "tradingagents_spike",
            "contract": "quant_evidence_v1",
            "domain": "quant_strict",
            "task": raw.get("task", {}),
        },
    }
    validation = QuantEvidenceContractValidator().validate(payload)
    if not validation.accepted:
        details = "; ".join(issue.message for issue in validation.issues)
        raise ValueError(f"TradingAgents export cannot become quant evidence: {details}")
    return payload


def _node(agent: Any) -> dict[str, Any]:
    if not isinstance(agent, dict):
        raise ValueError("TradingAgents agent entries must be objects.")
    node_id = str(agent.get("id") or "").strip()
    if not node_id:
        raise ValueError("TradingAgents agent entry requires id.")
    return {
        "id": node_id,
        "name": str(agent.get("role") or node_id),
        "type": "agent",
        "metadata": {
            "optimizable": node_id in {"researcher", "strategy_researcher", "risk_manager"},
            "tradingagents_role": agent.get("role"),
        },
    }


def _edges(agents: list[Any]) -> list[dict[str, Any]]:
    ids = [str(agent.get("id")) for agent in agents if isinstance(agent, dict) and agent.get("id")]
    return [{"source": source, "target": target, "type": "sequence"} for source, target in zip(ids, ids[1:])]


def _trace(agent: Any) -> dict[str, Any]:
    if not isinstance(agent, dict):
        raise ValueError("TradingAgents agent entries must be objects.")
    return {
        "node_id": str(agent.get("id")),
        "status": str(agent.get("status") or "succeeded"),
        "duration_ms": _optional_float(agent.get("duration_ms")),
        "cost": _optional_float(agent.get("cost")),
        "input_summary": str(agent.get("input") or ""),
        "output_summary": str(agent.get("output") or ""),
        "metrics": _numeric_dict(agent.get("metrics")),
        "metadata": {"role": agent.get("role")},
    }


def _config(raw: dict[str, Any]) -> dict[str, Any]:
    config = raw.get("strategy_config")
    if not isinstance(config, dict):
        return {}
    return dict(config)


def _numeric_dict(raw: Any) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, float] = {}
    for key, value in raw.items():
        if isinstance(value, int | float):
            result[str(key)] = float(value)
    return result


def _optional_float(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _metric_schema() -> dict[str, dict[str, Any]]:
    return {
        "total_return": {"direction": "higher", "category": "business", "weight": 0.2},
        "annual_return": {"direction": "higher", "category": "business", "weight": 0.1},
        "benchmark_return": {"direction": "reference", "category": "business", "weight": 0.0},
        "excess_return": {"direction": "higher", "category": "business", "weight": 0.2},
        "sharpe": {"direction": "higher", "category": "business", "weight": 0.3},
        "max_drawdown": {
            "direction": "lower",
            "category": "guardrail",
            "weight": 0.2,
            "threshold": 0.2,
            "is_guardrail": True,
        },
        "win_rate": {"direction": "higher", "category": "business", "weight": 0.05},
        "turnover": {"direction": "lower", "category": "guardrail", "weight": 0.05, "threshold": 3.0},
        "trade_count": {"direction": "bounded", "category": "data_quality", "weight": 0.0},
        "sample_count": {"direction": "higher", "category": "data_quality", "weight": 0.0},
        "latency_ms": {"direction": "lower", "category": "system", "weight": 0.0},
        "api_cost": {"direction": "lower", "category": "system", "weight": 0.0},
    }
