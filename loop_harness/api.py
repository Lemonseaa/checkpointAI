"""Optional HTTP API surface for the loop_harness."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loop_harness.adapter import (
    AdapterRegistry,
    DummyAdapter,
    OPCAgentAdapter,
    QuantResearchDemoAdapter,
)
from loop_harness.agent_config import AgentConfig, AgentConfigStore
from loop_harness.auth import APIKeyManager, BearerTokenAuth
from loop_harness.autonomy import AutoActionQueue, AutonomyActionStore, AutonomyQueueStateStore
from loop_harness.config_version import ConfigBranchStore, ConfigVersionService, ConfigVersionStore
from loop_harness.console import ApprovalInbox, BackupManager, ConsoleDashboard, ConsoleReadModel
from loop_harness.decision import DecisionKind, DecisionLogStore, DecisionRecord
from loop_harness.evidence import (
    CandidateBoundary,
    CandidateChange,
    EvidenceBaselineStore,
    EvidenceReviewPackage,
    HumanDecisionMemory,
    OptimizationGoalProfile,
    OptimizationGoalStore,
    ReviewPackageDecisionStore,
    ShadowReplayItem,
    ShadowReplayQueueStore,
    WorkflowContractValidator,
)
from loop_harness.external_agents import ExternalAgentConnection, ExternalAgentConnectionStore
from loop_harness.harness import EvidenceHarness
from loop_harness.learning import ObservationStore, SafetyFindingStore, ValidationSummaryStore
from loop_harness.logs import RawLogStore, SummaryLogStore
from loop_harness.loop_harness import LoopHarness
from loop_harness.metrics import MetricSchema, MetricSchemaStore
from loop_harness.optimization import ParameterSuggestionStore
from loop_harness.prompt import (
    PromptProposalStore,
    PromptVersionStore,
    Proposal,
    ProposalKind,
    ProposalPatch,
    ProposalStore,
    ProposalTargetType,
)
from loop_harness.recommendation import VersionRecommendationStore
from loop_harness.reporting import ReportGenerator
from loop_harness.scenario import ScenarioRegistry, ScenarioRunner, ScenarioStore
from loop_harness.shadow import ShadowResultStore, ShadowRunner
from loop_harness.user_profile import UserProfileStore

_uvicorn_server: Any

try:
    import uvicorn as _uvicorn
except ImportError:  # pragma: no cover - exercised only when optional server dependency is absent.
    class _MissingUvicorn:
        """Clear failure object for environments without uvicorn installed."""

        @staticmethod
        def run(*_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("uvicorn is required to serve the LoopHarness API")

    _uvicorn_server = _MissingUvicorn()
else:
    _uvicorn_server = _uvicorn


@dataclass(slots=True)
class FallbackApp:
    """Small app object used when FastAPI is not installed."""

    auth: BearerTokenAuth
    app_state: dict[str, Any] = field(default_factory=dict)
    routes: list[dict[str, str]] = field(default_factory=list)

    def authenticate(self, authorization: str | None) -> bool:
        """Validate a bearer token in fallback mode."""

        return self.auth.authenticate(authorization)


def create_app(
    loop_harness: LoopHarness | None = None,
    auth_manager: APIKeyManager | None = None,
    db_path: str | Path | None = None,
    backup_dir: str | Path | None = None,
    force_fallback: bool = False,
) -> Any:
    """Create a FastAPI app when available, otherwise return a fallback app."""

    active_loop_harness = loop_harness or LoopHarness.from_env()
    active_auth = BearerTokenAuth(auth_manager or APIKeyManager(initial_tokens=_initial_tokens_from_env()))
    active_db_path = Path(db_path or active_loop_harness.config.sqlite_path)
    active_backup_dir = Path(backup_dir or active_db_path.parent / "backups")
    if force_fallback:
        return _fallback_app(active_loop_harness, active_auth)
    try:
        from fastapi import (  # type: ignore[import-not-found]
            Depends,
            FastAPI,
            Header,
            HTTPException,
            Request,
        )
        from fastapi.responses import JSONResponse  # type: ignore[import-not-found]
    except ImportError:
        return _fallback_app(active_loop_harness, active_auth)

    app = FastAPI(title="LoopHarness Control Console API")

    @app.exception_handler(HTTPException)
    def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and {"code", "message", "details"}.issubset(detail):
            return JSONResponse(status_code=exc.status_code, content=detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": f"http.{exc.status_code}",
                "message": str(detail),
                "details": {},
            },
        )

    def require_auth(authorization: str | None = Header(default=None)) -> None:
        if not active_auth.authenticate(authorization):
            raise HTTPException(
                status_code=401,
                detail=_api_error(
                    "auth.invalid",
                    "Invalid or missing bearer token.",
                    {},
                ),
            )

    @app.get("/health")
    def health(_auth: None = Depends(require_auth)) -> dict[str, str]:
        return {"status": "healthy"}

    @app.get("/runs")
    def list_runs(_auth: None = Depends(require_auth)) -> list[dict[str, Any]]:
        return active_loop_harness.store.list_runs()

    @app.get("/metrics")
    def metrics(_auth: None = Depends(require_auth)) -> dict[str, Any]:
        return active_loop_harness.metrics.get_summary()

    @app.get("/api/health")
    def api_health(_auth: None = Depends(require_auth)) -> dict[str, Any]:
        try:
            return active_loop_harness.health_checker.generate_diagnostic_report().to_dict()
        except Exception as exc:
            return {
                "overall_status": "unhealthy",
                "checks": [
                    {
                        "component": "health_checker",
                        "status": "error",
                        "message": str(exc),
                        "details": {},
                    }
                ],
                "recommendations": ["检查数据库是否由不完整备份恢复，必要时恢复到更新的备份。"],
            }

    @app.get("/api/version")
    def api_version(_auth: None = Depends(require_auth)) -> dict[str, str]:
        return {"name": "Loop Harness", "version": "v5"}

    @app.get("/api/auth/check")
    def api_auth_check(_auth: None = Depends(require_auth)) -> dict[str, bool]:
        return {"authenticated": True}

    @app.post("/api/evidence/runs")
    def ingest_evidence_run(
        payload: dict[str, Any],
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        result = EvidenceHarness(active_db_path).ingest_payload(payload)
        return {
            "run_id": result.run.run_id,
            "workflow_id": result.run.workflow_id,
            "run_kind": result.run.run_kind.value,
            "trace_coverage": result.visualization.trace_coverage,
            "metric_coverage": result.visualization.metric_coverage,
            "black_box_node_ids": result.visualization.black_box_node_ids,
            "recommendation": result.report.recommendation.value,
            "summary": result.report.summary,
        }

    @app.get("/api/evidence/runs")
    def list_evidence_runs(
        workflow_id: str | None = None,
        _auth: None = Depends(require_auth),
    ) -> list[dict[str, Any]]:
        return [
            {
                "run": stored.run.model_dump(mode="json"),
                "visualization": stored.visualization.model_dump(mode="json"),
                "report": stored.report.model_dump(mode="json"),
            }
            for stored in EvidenceHarness(active_db_path).list_runs(workflow_id=workflow_id)
        ]

    @app.get("/api/evidence/runs/{run_id}")
    def evidence_run_detail(run_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        stored = EvidenceHarness(active_db_path).store.get_run(run_id)
        if stored is None:
            raise HTTPException(
                status_code=404,
                detail=_api_error("evidence.run_not_found", "Evidence run not found.", {"run_id": run_id}),
            )
        return {
            "run": stored.run.model_dump(mode="json"),
            "visualization": stored.visualization.model_dump(mode="json"),
            "report": stored.report.model_dump(mode="json"),
        }

    @app.get("/api/evidence/runs/{run_id}/visualization")
    def evidence_visualization(run_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        try:
            return EvidenceHarness(active_db_path).visualize(run_id).model_dump(mode="json")
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=_api_error("evidence.run_not_found", "Evidence run not found.", {"run_id": run_id}),
            ) from None

    @app.get("/api/evidence/runs/{run_id}/report")
    def evidence_report(run_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        try:
            return EvidenceHarness(active_db_path).report(run_id).model_dump(mode="json")
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=_api_error("evidence.run_not_found", "Evidence run not found.", {"run_id": run_id}),
            ) from None

    @app.get("/api/evidence/workflows/{workflow_id}/map")
    def evidence_workflow_map(workflow_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        try:
            return EvidenceHarness(active_db_path).workflow_map(workflow_id).model_dump(mode="json")
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=_api_error("evidence.workflow_not_found", "Evidence workflow not found.", {"workflow_id": workflow_id}),
            ) from None

    @app.get("/api/evidence/workflows/{workflow_id}/graph")
    def evidence_workflow_graph(workflow_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        try:
            return EvidenceHarness(active_db_path).graph_for_workflow(workflow_id).model_dump(mode="json")
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=_api_error(
                    "evidence.workflow_not_found",
                    "Evidence workflow graph not found.",
                    {"workflow_id": workflow_id},
                ),
            ) from None

    @app.get("/api/evidence/runs/{run_id}/graph")
    def evidence_run_graph(run_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        try:
            return EvidenceHarness(active_db_path).graph_for_run(run_id).model_dump(mode="json")
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=_api_error("evidence.run_not_found", "Evidence run graph not found.", {"run_id": run_id}),
            ) from None

    @app.get("/api/evidence/workflows/{workflow_id}/charts/optimization")
    def evidence_workflow_optimization_chart(workflow_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        try:
            return EvidenceHarness(active_db_path).optimization_chart(workflow_id).model_dump(mode="json")
        except ValueError as exc:
            raise HTTPException(
                status_code=404,
                detail=_api_error(
                    "evidence.chart_not_found",
                    str(exc),
                    {"workflow_id": workflow_id},
                ),
            ) from None

    @app.post("/api/evidence/charts/optimization")
    def evidence_explicit_optimization_chart(
        payload: dict[str, Any],
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        baseline_run_id = str(payload.get("baseline_run_id", ""))
        candidate_run_ids = [str(item) for item in payload.get("candidate_run_ids", [])]
        if not baseline_run_id or not candidate_run_ids:
            raise HTTPException(
                status_code=400,
                detail=_api_error(
                    "evidence.chart_missing_field",
                    "baseline_run_id and candidate_run_ids are required.",
                    {},
                ),
            )
        try:
            return EvidenceHarness(active_db_path).optimization_chart_for_runs(
                baseline_run_id,
                candidate_run_ids,
            ).model_dump(mode="json")
        except ValueError as exc:
            raise HTTPException(
                status_code=404,
                detail=_api_error("evidence.run_not_found", str(exc), {}),
            ) from None

    @app.post("/api/evidence/review-packages")
    def evidence_review_package(
        payload: dict[str, Any],
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        baseline_run_id = str(payload.get("baseline_run_id", ""))
        candidate_run_ids = [str(item) for item in payload.get("candidate_run_ids", [])]
        if not baseline_run_id or not candidate_run_ids:
            raise HTTPException(
                status_code=400,
                detail=_api_error(
                    "evidence.package_missing_field",
                    "baseline_run_id and candidate_run_ids are required.",
                    {},
                ),
            )
        try:
            return EvidenceHarness(active_db_path).review_package_for_runs(
                baseline_run_id,
                candidate_run_ids,
            ).model_dump(mode="json")
        except ValueError as exc:
            raise HTTPException(
                status_code=404,
                detail=_api_error("evidence.run_not_found", str(exc), {}),
            ) from None

    @app.post("/api/evidence/review-packages/validate")
    def evidence_review_package_validate(
        payload: dict[str, Any],
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        try:
            package = EvidenceReviewPackage.model_validate(payload)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=_api_error("evidence.package_invalid", str(exc), {}),
            ) from None
        return EvidenceHarness(active_db_path).validate_review_package(package).model_dump(mode="json")

    @app.post("/api/evidence/review-packages/submit")
    def evidence_review_package_submit(
        payload: dict[str, Any],
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        reason = str(payload.get("reason", "")).strip()
        package_payload = payload.get("package")
        if not reason or not isinstance(package_payload, dict):
            raise HTTPException(
                status_code=400,
                detail=_api_error(
                    "evidence.review_submit_missing_field",
                    "package and reason are required.",
                    {},
                ),
            )
        try:
            package = EvidenceReviewPackage.model_validate(package_payload)
            return EvidenceHarness(active_db_path).submit_review_package(package, reason).model_dump(mode="json")
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=_api_error("evidence.review_submit_failed", str(exc), {}),
            ) from None

    @app.get("/api/evidence/review-decisions")
    def evidence_review_decisions(
        scenario_id: str | None = None,
        status: str | None = None,
        _auth: None = Depends(require_auth),
    ) -> list[dict[str, Any]]:
        try:
            return [
                decision.model_dump(mode="json")
                for decision in EvidenceHarness(active_db_path).list_review_package_decisions(
                    scenario_id=scenario_id,
                    status=status,
                )
            ]
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=_api_error("evidence.review_decision_invalid_filter", str(exc), {"status": status}),
            ) from None

    @app.get("/api/evidence/review-packages/{package_id}/decision")
    def evidence_review_package_decision(
        package_id: str,
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        try:
            return EvidenceHarness(active_db_path).review_package_decision_for_package(package_id).model_dump(mode="json")
        except ValueError as exc:
            raise HTTPException(
                status_code=404,
                detail=_api_error(
                    "evidence.review_package_decision_not_found",
                    str(exc),
                    {"package_id": package_id},
                ),
            ) from None

    @app.post("/api/evidence/review-decisions/{decision_id}/approve")
    def evidence_review_decision_approve(
        decision_id: str,
        payload: dict[str, Any] | None = None,
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        comment = str((payload or {}).get("comment", "")).strip()
        if not comment:
            raise HTTPException(
                status_code=400,
                detail=_api_error("validation.operator_comment_required", "Operator comment is required.", {}),
            )
        try:
            decision = EvidenceHarness(active_db_path).approve_review_package(decision_id, comment)
        except ValueError as exc:
            if "already" in str(exc):
                raise HTTPException(
                    status_code=400,
                    detail=_api_error(
                        "evidence.review_decision_state_conflict",
                        str(exc),
                        {"decision_id": decision_id},
                    ),
                ) from None
            raise HTTPException(
                status_code=404,
                detail=_api_error("evidence.review_decision_not_found", str(exc), {"decision_id": decision_id}),
            ) from None
        _record_decision(
            db_path=active_db_path,
            source_id=decision_id,
            source_type="evidence_review_package",
            kind=DecisionKind.APPROVE,
            scenario_id=decision.scenario_id,
            action="approve_review_package",
            comment=comment,
            after=decision.model_dump(mode="json"),
        )
        return decision.model_dump(mode="json")

    @app.post("/api/evidence/review-decisions/{decision_id}/reject")
    def evidence_review_decision_reject(
        decision_id: str,
        payload: dict[str, Any] | None = None,
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        comment = str((payload or {}).get("comment", "")).strip()
        if not comment:
            raise HTTPException(
                status_code=400,
                detail=_api_error("validation.operator_comment_required", "Operator comment is required.", {}),
            )
        try:
            decision = EvidenceHarness(active_db_path).reject_review_package(decision_id, comment)
        except ValueError as exc:
            if "already" in str(exc):
                raise HTTPException(
                    status_code=400,
                    detail=_api_error(
                        "evidence.review_decision_state_conflict",
                        str(exc),
                        {"decision_id": decision_id},
                    ),
                ) from None
            raise HTTPException(
                status_code=404,
                detail=_api_error("evidence.review_decision_not_found", str(exc), {"decision_id": decision_id}),
            ) from None
        _record_decision(
            db_path=active_db_path,
            source_id=decision_id,
            source_type="evidence_review_package",
            kind=DecisionKind.REJECT,
            scenario_id=decision.scenario_id,
            action="reject_review_package",
            comment=comment,
            after=decision.model_dump(mode="json"),
        )
        return decision.model_dump(mode="json")

    @app.post("/api/evidence/import/quant-csv")
    def evidence_import_quant_csv(payload: dict[str, Any], _auth: None = Depends(require_auth)) -> dict[str, Any]:
        try:
            path = str(payload["path"])
            workflow_id = str(payload["workflow_id"])
        except KeyError as exc:
            missing = str(exc).strip("'")
            raise HTTPException(
                status_code=400,
                detail=_api_error("evidence.import_missing_field", "Missing import field.", {"field": missing}),
            ) from None
        try:
            return EvidenceHarness(active_db_path).ingest_quant_csv(
                path,
                workflow_id=workflow_id,
                scenario_id=str(payload.get("scenario_id", "quant")),
                run_kind=str(payload.get("run_kind", "historical")),
            ).model_dump(mode="json")
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=_api_error("evidence.import_failed", str(exc), {}),
            ) from None

    @app.get("/api/evidence/runs/{run_id}/gaps")
    def evidence_gap_report(run_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        try:
            return EvidenceHarness(active_db_path).gap_report(run_id).model_dump(mode="json")
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=_api_error("evidence.run_not_found", "Evidence run not found.", {"run_id": run_id}),
            ) from None

    @app.get("/api/evidence/runs/{run_id}/nodes/{node_id}")
    def evidence_node_detail(run_id: str, node_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        try:
            return EvidenceHarness(active_db_path).node_detail(run_id, node_id).model_dump(mode="json")
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=_api_error(
                    "evidence.node_not_found",
                    "Evidence node not found.",
                    {"run_id": run_id, "node_id": node_id},
                ),
            ) from None

    @app.post("/api/evidence/contracts/validate")
    def evidence_contract_validate(payload: dict[str, Any], _auth: None = Depends(require_auth)) -> dict[str, Any]:
        return WorkflowContractValidator().validate(payload).model_dump(mode="json")

    @app.post("/api/evidence/boundary/classify")
    def evidence_boundary_classify(payload: dict[str, Any], _auth: None = Depends(require_auth)) -> dict[str, Any]:
        return CandidateBoundary().classify(CandidateChange.model_validate(payload)).model_dump(mode="json")

    @app.post("/api/evidence/goals/{scenario_id}")
    def save_evidence_goal(
        scenario_id: str,
        payload: dict[str, Any],
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        profile = OptimizationGoalProfile(
            scenario_id=scenario_id,
            primary_metrics=[str(item) for item in payload.get("primary_metrics", [])],
            guardrail_metrics=[str(item) for item in payload.get("guardrail_metrics", [])],
            max_cost_increase=float(payload.get("max_cost_increase", 0.0)),
            max_risk_level=str(payload.get("max_risk_level", "approval")),
            preferences=dict(payload.get("preferences", {})),
        )
        return OptimizationGoalStore(active_db_path).save(profile).model_dump(mode="json")

    @app.get("/api/evidence/goals/{scenario_id}")
    def get_evidence_goal(scenario_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        profile = OptimizationGoalStore(active_db_path).get(scenario_id)
        if profile is None:
            raise HTTPException(
                status_code=404,
                detail=_api_error("evidence.goal_not_found", "Optimization goal profile not found.", {"scenario_id": scenario_id}),
            )
        return profile.model_dump(mode="json")

    @app.get("/api/evidence/decision-memory/{scenario_id}")
    def evidence_decision_memory(scenario_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        return HumanDecisionMemory(active_db_path).summarize(scenario_id).model_dump(mode="json")

    @app.post("/api/evidence/shadow-queue")
    def enqueue_evidence_shadow(payload: dict[str, Any], _auth: None = Depends(require_auth)) -> dict[str, Any]:
        item = ShadowReplayItem.model_validate(payload)
        ShadowReplayQueueStore(active_db_path).enqueue(item)
        return item.model_dump(mode="json")

    @app.get("/api/evidence/shadow-queue")
    def list_evidence_shadow_queue(
        scenario_id: str | None = None,
        status: str | None = None,
        _auth: None = Depends(require_auth),
    ) -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json")
            for item in ShadowReplayQueueStore(active_db_path).list(scenario_id=scenario_id, status=status)
        ]

    @app.post("/api/evidence/workflows/{workflow_id}/baseline")
    def set_evidence_baseline(
        workflow_id: str,
        payload: dict[str, Any],
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        baseline_run_id = str(payload.get("baseline_run_id", ""))
        reason = str(payload.get("reason", "")).strip()
        if not baseline_run_id or not reason:
            raise HTTPException(
                status_code=400,
                detail=_api_error(
                    "evidence.baseline_missing_field",
                    "baseline_run_id and reason are required.",
                    {},
                ),
            )
        stored = EvidenceHarness(active_db_path).store.get_run(baseline_run_id)
        if stored is None or stored.run.workflow_id != workflow_id:
            raise HTTPException(
                status_code=404,
                detail=_api_error(
                    "evidence.run_not_found",
                    "Baseline run not found for workflow.",
                    {"workflow_id": workflow_id, "baseline_run_id": baseline_run_id},
                ),
            )
        return EvidenceBaselineStore(active_db_path).set_baseline(
            workflow_id=workflow_id,
            baseline_run_id=baseline_run_id,
            reason=reason,
        ).model_dump(mode="json")

    @app.get("/api/evidence/workflows/{workflow_id}/baseline")
    def get_evidence_baseline(workflow_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        baseline = EvidenceBaselineStore(active_db_path).get_baseline(workflow_id)
        if baseline is None:
            raise HTTPException(
                status_code=404,
                detail=_api_error(
                    "evidence.baseline_not_found",
                    "Evidence baseline not found.",
                    {"workflow_id": workflow_id},
                ),
            )
        return baseline.model_dump(mode="json")

    @app.post("/api/evidence/compare")
    def compare_evidence_runs(
        payload: dict[str, Any],
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        try:
            candidate_run_id = str(payload["candidate_run_id"])
            baseline_run_id = payload.get("baseline_run_id")
            if baseline_run_id is None:
                candidate = EvidenceHarness(active_db_path).store.get_run(candidate_run_id)
                if candidate is None:
                    raise ValueError(f"Unknown candidate run: {candidate_run_id}")
                baseline = EvidenceBaselineStore(active_db_path).get_baseline(candidate.run.workflow_id)
                if baseline is None:
                    raise KeyError("baseline_run_id")
                baseline_run_id = baseline.baseline_run_id
            return EvidenceHarness(active_db_path).compare(
                baseline_run_id=str(baseline_run_id),
                candidate_run_id=candidate_run_id,
            ).model_dump(mode="json")
        except KeyError as exc:
            missing = str(exc).strip("'")
            raise HTTPException(
                status_code=400,
                detail=_api_error("evidence.compare_missing_field", "Missing comparison field.", {"field": missing}),
            ) from None
        except ValueError as exc:
            raise HTTPException(
                status_code=404,
                detail=_api_error("evidence.run_not_found", str(exc), {}),
            ) from None

    @app.post("/api/evidence/compare/export")
    def export_evidence_comparison(
        payload: dict[str, Any],
        _auth: None = Depends(require_auth),
    ) -> dict[str, str]:
        try:
            baseline_run_id = str(payload["baseline_run_id"])
            candidate_run_id = str(payload["candidate_run_id"])
        except KeyError as exc:
            missing = str(exc).strip("'")
            raise HTTPException(
                status_code=400,
                detail=_api_error("evidence.compare_missing_field", "Missing comparison field.", {"field": missing}),
            ) from None
        try:
            return {
                "report": EvidenceHarness(active_db_path).export_comparison_markdown(
                    baseline_run_id=baseline_run_id,
                    candidate_run_id=candidate_run_id,
                )
            }
        except ValueError as exc:
            raise HTTPException(
                status_code=404,
                detail=_api_error("evidence.run_not_found", str(exc), {}),
            ) from None

    @app.post("/api/evidence/metrics/{scenario_id}")
    def save_evidence_metric_mapping(
        scenario_id: str,
        payload: list[dict[str, Any]],
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        schemas = [MetricSchema.model_validate(item) for item in payload]
        MetricSchemaStore(active_db_path).save_for_scenario(scenario_id, schemas)
        return {"scenario_id": scenario_id, "saved": len(schemas)}

    @app.get("/api/evidence/metrics/{scenario_id}")
    def list_evidence_metric_mapping(scenario_id: str, _auth: None = Depends(require_auth)) -> list[dict[str, Any]]:
        return [
            schema.model_dump(mode="json")
            for schema in MetricSchemaStore(active_db_path).list_for_scenario(scenario_id)
        ]

    @app.post("/api/evidence/proposals")
    def create_evidence_proposal(
        payload: dict[str, Any],
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        baseline_run_id = str(payload.get("baseline_run_id", ""))
        candidate_run_id = str(payload.get("candidate_run_id", ""))
        scenario_id = str(payload.get("scenario_id", "") or "evidence")
        if not baseline_run_id or not candidate_run_id:
            raise HTTPException(
                status_code=400,
                detail=_api_error(
                    "evidence.proposal_missing_field",
                    "baseline_run_id and candidate_run_id are required.",
                    {},
                ),
            )
        harness = EvidenceHarness(active_db_path)
        report = harness.compare(baseline_run_id=baseline_run_id, candidate_run_id=candidate_run_id)
        quality = report.evidence.get("quality", {})
        if report.recommendation.value != "approve" or quality.get("status") == "rejected":
            raise HTTPException(
                status_code=400,
                detail=_api_error(
                    "evidence.proposal_not_allowed",
                    "Evidence comparison is not strong enough to create an approval proposal.",
                    {
                        "recommendation": report.recommendation.value,
                        "quality": quality,
                    },
                ),
            )
        proposal = Proposal(
            scenario_id=scenario_id,
            proposal_kind=ProposalKind.EVIDENCE,
            target_type=ProposalTargetType.DEPLOYMENT,
            target_id=f"{report.workflow_id}:{candidate_run_id}",
            patch=ProposalPatch(
                operation="replace",
                before={"baseline_run_id": baseline_run_id},
                after={"candidate_run_id": candidate_run_id},
            ),
            reason=report.summary,
            expected_metric="objective_score",
            metadata={
                "workflow_id": report.workflow_id,
                "baseline_run_id": baseline_run_id,
                "candidate_run_id": candidate_run_id,
                "quality": quality,
                "comparison": report.comparison.model_dump(mode="json") if report.comparison else None,
            },
        )
        ProposalStore(active_db_path).create(proposal)
        return proposal.model_dump(mode="json")

    @app.get("/api/console/snapshot")
    def console_snapshot(
        scenario_id: str | None = None,
        all_scenarios: bool = False,
        reason: str | None = None,
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        return ConsoleReadModel(active_db_path).snapshot(
            scenario_id=scenario_id,
            allow_cross_scenario=all_scenarios,
            reason=reason,
        ).model_dump(mode="json")

    @app.get("/api/approvals")
    def list_approvals(
        scenario_id: str | None = None,
        _auth: None = Depends(require_auth),
    ) -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json")
            for item in ApprovalInbox(active_db_path).list_items(scenario_id=scenario_id)
        ]

    @app.get("/api/approvals/{approval_id}")
    def approval_detail(approval_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        item = _approval_item(approval_id, active_db_path)
        if item is None:
            raise HTTPException(status_code=404, detail="Approval item not found.")
        return item

    @app.post("/api/approvals/{approval_id}/approve")
    def approve_item(
        approval_id: str,
        payload: dict[str, Any] | None = None,
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        item = _approval_item(approval_id, active_db_path)
        comment = _required_comment(payload, active_db_path, approval_id, item)
        if item is None:
            raise HTTPException(
                status_code=404,
                detail=_api_error(
                    "approval.not_found",
                    "Approval item not found or already resolved.",
                    {"source_id": approval_id},
                ),
            )
        updated = ApprovalInbox(active_db_path).approve(
            approval_id,
            reason=comment,
        )
        _record_decision(
            db_path=active_db_path,
            source_id=approval_id,
            source_type=str(item["item_type"]),
            kind=DecisionKind.APPROVE,
            scenario_id=str(item["scenario_id"]),
            action="approve",
            comment=comment,
            before=item,
            after={"updated": updated},
        )
        return {"id": approval_id, "updated": updated}

    @app.post("/api/approvals/{approval_id}/reject")
    def reject_item(
        approval_id: str,
        payload: dict[str, Any] | None = None,
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        item = _approval_item(approval_id, active_db_path)
        comment = _required_comment(payload, active_db_path, approval_id, item)
        if item is None:
            raise HTTPException(
                status_code=404,
                detail=_api_error(
                    "approval.not_found",
                    "Approval item not found or already resolved.",
                    {"source_id": approval_id},
                ),
            )
        updated = ApprovalInbox(active_db_path).reject(
            approval_id,
            reason=comment,
        )
        _record_decision(
            db_path=active_db_path,
            source_id=approval_id,
            source_type=str(item["item_type"]),
            kind=DecisionKind.REJECT,
            scenario_id=str(item["scenario_id"]),
            action="reject",
            comment=comment,
            before=item,
            after={"updated": updated},
        )
        return {"id": approval_id, "updated": updated}

    @app.get("/api/runs")
    def api_runs(
        scenario_id: str | None = None,
        _auth: None = Depends(require_auth),
    ) -> list[dict[str, Any]]:
        scenarios = [scenario_id] if scenario_id else [scenario.id for scenario in ScenarioStore(active_db_path).list()]
        rows: list[dict[str, Any]] = []
        summaries = SummaryLogStore(active_db_path)
        for active_scenario_id in scenarios:
            rows.extend(summaries.query_by_scenario(active_scenario_id))
        return rows

    @app.get("/api/runs/{run_id}")
    def api_run_detail(run_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        return ConsoleDashboard(active_db_path).run_report(run_id).model_dump(mode="json")

    @app.post("/api/runs")
    def api_trigger_run(
        payload: dict[str, Any],
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        result = _scenario_runner(active_db_path).run_scenario(
            scenario_id=str(payload["scenario_id"]),
            task=str(payload["task"]),
            context=dict(payload.get("context", {})),
            config=dict(payload.get("config", {})),
        )
        return {
            "scenario_id": result.scenario_id,
            "run_id": result.run_id,
            "task": result.task,
            "status": result.status,
            "metrics": result.metrics,
            "value_summary": result.value_summary,
            "answer": result.answer,
        }

    @app.get("/api/backups")
    def list_backups(_auth: None = Depends(require_auth)) -> list[dict[str, Any]]:
        return [
            {**backup.model_dump(mode="json"), "path": str(backup.path)}
            for backup in BackupManager(active_db_path, active_backup_dir).list_backups()
        ]

    @app.post("/api/backups")
    def create_backup(
        payload: dict[str, Any] | None = None,
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        backup = BackupManager(active_db_path, active_backup_dir).create_backup(
            label=str((payload or {}).get("label", "manual")),
        )
        return {**backup.model_dump(mode="json"), "path": str(backup.path)}

    @app.post("/api/backups/{backup_id}/restore")
    def restore_backup(
        backup_id: str,
        payload: dict[str, Any] | None = None,
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        if str((payload or {}).get("confirm", "")).strip() != "RESTORE":
            _record_decision(
                db_path=active_db_path,
                source_id=backup_id,
                source_type="backup",
                kind=DecisionKind.ERROR,
                scenario_id=None,
                action="restore_backup",
                comment="Backup restore rejected because confirm=RESTORE was not provided.",
                details={"required_confirm": "RESTORE"},
            )
            raise HTTPException(
                status_code=400,
                detail=_api_error(
                    "backup.restore_confirmation_required",
                    "Backup restore requires confirm=RESTORE.",
                    {"backup_id": backup_id},
                ),
            )
        prior_decisions = DecisionLogStore(active_db_path).list(source_id=backup_id)
        restored, safety_backup = BackupManager(active_db_path, active_backup_dir).restore_with_safety(backup_id)
        if not restored:
            _record_decision(
                db_path=active_db_path,
                source_id=backup_id,
                source_type="backup",
                kind=DecisionKind.ERROR,
                scenario_id=None,
                action="restore_backup",
                comment="Backup restore failed because the backup id was not found.",
            )
            raise HTTPException(
                status_code=404,
                detail=_api_error("backup.not_found", "Backup not found.", {"backup_id": backup_id}),
            )
        for decision in prior_decisions:
            DecisionLogStore(active_db_path).record(decision)
        _record_decision(
            db_path=active_db_path,
            source_id=backup_id,
            source_type="backup",
            kind=DecisionKind.SYSTEM,
            scenario_id=None,
            action="restore_backup",
            comment="Backup restored after explicit operator confirmation.",
            result={"restored": restored},
            details={"pre_restore_backup_id": safety_backup.id if safety_backup else None},
        )
        return {
            "id": backup_id,
            "restored": restored,
            "pre_restore_backup_id": safety_backup.id if safety_backup else None,
        }

    @app.get("/api/scenarios")
    def api_scenarios(_auth: None = Depends(require_auth)) -> list[dict[str, Any]]:
        return [scenario.model_dump(mode="json") for scenario in ScenarioStore(active_db_path).list()]

    @app.get("/api/scenarios/{scenario_id}")
    def api_scenario(scenario_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        scenario = ScenarioStore(active_db_path).get(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=404, detail="Scenario not found.")
        return scenario.model_dump(mode="json")

    @app.post("/api/scenarios/{scenario_id}/archive")
    def api_archive_scenario(
        scenario_id: str,
        payload: dict[str, Any] | None = None,
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        archived = ScenarioStore(active_db_path).archive(
            scenario_id,
            reason=str((payload or {}).get("reason", "Archived from Web API.")),
        )
        return {"id": scenario_id, "archived": archived}

    @app.get("/api/adapters")
    def api_adapters(_auth: None = Depends(require_auth)) -> list[dict[str, Any]]:
        return [adapter.model_dump(mode="json") for adapter in _adapter_registry().describe()]

    @app.get("/api/learning/observations")
    def api_learning_observations(
        scenario_id: str | None = None,
        business_line_id: str | None = None,
        _auth: None = Depends(require_auth),
    ) -> list[dict[str, Any]]:
        return [
            observation.model_dump(mode="json")
            for observation in ObservationStore(active_db_path).list(
                scenario_id=scenario_id,
                business_line_id=business_line_id,
            )
        ]

    @app.get("/api/learning/safety-findings")
    def api_learning_safety_findings(
        scenario_id: str | None = None,
        _auth: None = Depends(require_auth),
    ) -> list[dict[str, Any]]:
        return [
            finding.model_dump(mode="json")
            for finding in SafetyFindingStore(active_db_path).list(scenario_id=scenario_id)
        ]

    @app.get("/api/learning/validations")
    def api_learning_validations(
        scenario_id: str | None = None,
        _auth: None = Depends(require_auth),
    ) -> list[dict[str, Any]]:
        return [
            validation.model_dump(mode="json")
            for validation in ValidationSummaryStore(active_db_path).list(scenario_id=scenario_id)
        ]

    @app.get("/api/config/versions")
    def api_config_versions(
        scenario_id: str | None = None,
        _auth: None = Depends(require_auth),
    ) -> list[dict[str, Any]]:
        return [
            version.model_dump(mode="json")
            for version in ConfigVersionStore(active_db_path).list(scenario_id=scenario_id)
        ]

    @app.post("/api/config/versions/{version_id}/lock")
    def api_lock_config_version(
        version_id: str,
        payload: dict[str, Any] | None = None,
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        service = ConfigVersionService(ConfigVersionStore(active_db_path), ConfigBranchStore(active_db_path))
        reason = str((payload or {}).get("reason", "Locked from control console."))
        return service.lock_version(version_id, reason=reason).model_dump(mode="json")

    @app.post("/api/config/branches")
    def api_create_config_branch(
        payload: dict[str, Any],
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        service = ConfigVersionService(ConfigVersionStore(active_db_path), ConfigBranchStore(active_db_path))
        return service.create_branch(
            scenario_id=str(payload["scenario_id"]),
            business_line_id=str(payload["business_line_id"]),
            name=str(payload["name"]),
            base_version_id=str(payload["base_version_id"]),
        ).model_dump(mode="json")

    @app.get("/api/agent-configs")
    def api_agent_configs(
        business_line_id: str | None = None,
        _auth: None = Depends(require_auth),
    ) -> list[dict[str, Any]]:
        return [
            config.model_dump(mode="json")
            for config in AgentConfigStore(active_db_path).list(business_line_id=business_line_id)
        ]

    @app.post("/api/agent-configs")
    def api_save_agent_config(payload: dict[str, Any], _auth: None = Depends(require_auth)) -> dict[str, str]:
        config = AgentConfig(**payload)
        config_id = AgentConfigStore(active_db_path).save(config)
        return {"id": config_id}

    @app.get("/api/external-agents")
    def api_external_agents(
        business_line_id: str | None = None,
        _auth: None = Depends(require_auth),
    ) -> list[dict[str, Any]]:
        return [
            connection.model_dump(mode="json")
            for connection in ExternalAgentConnectionStore(active_db_path).list(business_line_id=business_line_id)
        ]

    @app.post("/api/external-agents")
    def api_save_external_agent(payload: dict[str, Any], _auth: None = Depends(require_auth)) -> dict[str, str]:
        connection = ExternalAgentConnection(**payload)
        connection_id = ExternalAgentConnectionStore(active_db_path).save(connection)
        return {"id": connection_id}

    @app.get("/api/user-profile")
    def api_user_profile(_auth: None = Depends(require_auth)) -> dict[str, Any]:
        profile = UserProfileStore(_profile_dir(active_db_path), active_db_path)
        return {
            "formal_profile": profile.read_formal_profile(),
            "suggested_notes": profile.read_suggested_notes(),
            "versions": [version.model_dump(mode="json") for version in profile.list_versions()],
        }

    @app.post("/api/user-profile")
    def api_save_user_profile(payload: dict[str, Any], _auth: None = Depends(require_auth)) -> dict[str, Any]:
        content = str(payload.get("content", "")).strip()
        reason = str(payload.get("reason", "")).strip()
        if not content or not reason:
            raise HTTPException(
                status_code=400,
                detail=_api_error(
                    "user_profile.missing_field",
                    "content and reason are required.",
                    {},
                ),
            )
        profile = UserProfileStore(_profile_dir(active_db_path), active_db_path)
        version = profile.save_formal_profile(
            content=content,
            actor="human",
            reason=reason,
        )
        return version.model_dump(mode="json")

    @app.post("/api/user-profile/suggest")
    def api_suggest_user_profile(payload: dict[str, Any], _auth: None = Depends(require_auth)) -> dict[str, Any]:
        scenario_id = payload.get("scenario_id")
        scenario_filter = str(scenario_id) if scenario_id else None
        decisions = DecisionLogStore(active_db_path).list(scenario_id=scenario_filter)
        comments = [record.comment for record in decisions if record.comment.strip()]
        profile = UserProfileStore(_profile_dir(active_db_path), active_db_path)
        content = _suggested_profile_notes(scenario_filter, comments)
        notes = profile.save_suggested_notes(content, actor="hermes")
        return notes.model_dump(mode="json")

    @app.get("/api/reports/latest")
    def api_latest_report(
        scenario_id: str | None = None,
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        return {"report": ReportGenerator(active_db_path).latest(scenario_id=scenario_id)}

    @app.get("/api/reports/runs/{run_id}")
    def api_run_report(run_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        return {"report": ReportGenerator(active_db_path).run(run_id)}

    @app.get("/api/reports/proposals/{proposal_id}")
    def api_proposal_report(proposal_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        return {"report": ReportGenerator(active_db_path).proposal(proposal_id)}

    @app.get("/api/reports/recommendations/{recommendation_id}")
    def api_recommendation_report(
        recommendation_id: str,
        _auth: None = Depends(require_auth),
    ) -> dict[str, Any]:
        return {"report": ReportGenerator(active_db_path).recommendation(recommendation_id)}

    @app.get("/api/shadows")
    def api_shadows(
        scenario_id: str | None = None,
        _auth: None = Depends(require_auth),
    ) -> list[dict[str, Any]]:
        return [
            shadow.model_dump(mode="json")
            for shadow in ShadowResultStore(active_db_path).list(scenario_id=scenario_id)
        ]

    @app.get("/api/shadows/{shadow_id}")
    def api_shadow_detail(shadow_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        shadow = ShadowResultStore(active_db_path).get(shadow_id)
        if shadow is None:
            raise HTTPException(status_code=404, detail="Shadow result not found.")
        return shadow.model_dump(mode="json")

    @app.post("/api/shadows")
    def api_run_shadow(payload: dict[str, Any], _auth: None = Depends(require_auth)) -> dict[str, Any]:
        proposal_id = str(payload["proposal_id"])
        proposal = PromptProposalStore(active_db_path).get(proposal_id)
        if proposal is None:
            _record_decision(
                db_path=active_db_path,
                source_id=proposal_id,
                source_type="prompt_proposal",
                kind=DecisionKind.ERROR,
                scenario_id=None,
                action="run_shadow",
                comment="Shadow run rejected because prompt proposal was not found.",
            )
            raise HTTPException(
                status_code=404,
                detail=_api_error(
                    "shadow.proposal_not_found",
                    "Prompt proposal not found.",
                    {"proposal_id": proposal_id},
                ),
            )
        result = ShadowRunner(
            scenarios=_scenario_registry(active_db_path),
            adapters=_adapter_registry(),
            versions=PromptVersionStore(active_db_path),
            results=ShadowResultStore(active_db_path),
            task=str(payload.get("task", "analyze_signal")),
            context=dict(payload.get("context", {})),
            metric_schema_store=MetricSchemaStore(active_db_path),
        ).run(proposal)
        if result.status == "failed":
            _record_decision(
                db_path=active_db_path,
                source_id=proposal.id,
                source_type="prompt_proposal",
                kind=DecisionKind.ERROR,
                scenario_id=proposal.scenario_id,
                action="run_shadow",
                comment="Shadow run failed and was recorded for audit.",
                result=result.model_dump(mode="json"),
            )
        return result.model_dump(mode="json")

    @app.get("/api/autonomy/actions")
    def api_autonomy_actions(
        scenario_id: str | None = None,
        status: str | None = None,
        _auth: None = Depends(require_auth),
    ) -> list[dict[str, Any]]:
        from loop_harness.autonomy import AutonomyActionStatus

        try:
            action_status = AutonomyActionStatus(status) if status else None
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=_api_error(
                    "autonomy.invalid_status",
                    "Invalid autonomy action status.",
                    {"status": status},
                ),
            ) from exc
        return [
            action.model_dump(mode="json")
            for action in AutonomyActionStore(active_db_path).list(
                scenario_id=scenario_id,
                status=action_status,
            )
        ]

    @app.get("/api/autonomy/actions/{action_id}")
    def api_autonomy_action_detail(action_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        action = AutonomyActionStore(active_db_path).get(action_id)
        if action is None:
            raise HTTPException(
                status_code=404,
                detail=_api_error("autonomy.action_not_found", "Autonomy action not found.", {"action_id": action_id}),
            )
        return action.model_dump(mode="json")

    @app.get("/api/autonomy/queue/status")
    def api_autonomy_queue_status(_auth: None = Depends(require_auth)) -> dict[str, Any]:
        actions = AutonomyActionStore(active_db_path)
        state = AutonomyQueueStateStore(active_db_path)
        return {
            "paused": state.is_paused(),
            "pending_count": len(actions.list(status=_autonomy_status("pending"))),
            "running_count": len(actions.list(status=_autonomy_status("running"))),
        }

    @app.post("/api/autonomy/queue/pause")
    def api_autonomy_queue_pause(_auth: None = Depends(require_auth)) -> dict[str, Any]:
        AutonomyQueueStateStore(active_db_path).pause()
        _record_decision(
            db_path=active_db_path,
            source_id="autonomy_queue",
            source_type="autonomy_queue",
            kind=DecisionKind.SYSTEM,
            scenario_id=None,
            action="pause_autonomy_queue",
            comment="Operator paused autonomy queue processing.",
        )
        return api_autonomy_queue_status()

    @app.post("/api/autonomy/queue/resume")
    def api_autonomy_queue_resume(_auth: None = Depends(require_auth)) -> dict[str, Any]:
        AutonomyQueueStateStore(active_db_path).resume()
        _record_decision(
            db_path=active_db_path,
            source_id="autonomy_queue",
            source_type="autonomy_queue",
            kind=DecisionKind.SYSTEM,
            scenario_id=None,
            action="resume_autonomy_queue",
            comment="Operator resumed autonomy queue processing.",
        )
        return api_autonomy_queue_status()

    @app.post("/api/autonomy/actions/{action_id}/process")
    def api_process_autonomy_action(action_id: str, _auth: None = Depends(require_auth)) -> dict[str, Any]:
        actions = AutonomyActionStore(active_db_path)
        action = actions.get(action_id)
        if action is None:
            raise HTTPException(
                status_code=404,
                detail=_api_error("autonomy.action_not_found", "Autonomy action not found.", {"action_id": action_id}),
            )
        queue = AutoActionQueue(
            actions=actions,
            decisions=DecisionLogStore(active_db_path),
            state=AutonomyQueueStateStore(active_db_path),
        )
        if queue.is_paused():
            return {"paused": True, "action": action.model_dump(mode="json")}

        def audit_only_handler(item: Any) -> dict[str, Any]:
            return {
                "mode": "audit_only",
                "applied": False,
                "proposal_id": item.proposal_id,
                "checkpoint_id": item.checkpoint_id,
                "message": "No live prompt or strategy was changed by this V6 console drill.",
            }

        if action.status.value != "pending":
            return {"paused": False, "action": action.model_dump(mode="json")}
        processed = queue.process(action.id, audit_only_handler)
        selected = actions.get(action_id) if processed is not None else action
        return {"paused": False, "action": selected.model_dump(mode="json") if selected else None}

    setattr(app, "loop_harness", active_loop_harness)
    setattr(app, "auth", active_auth)
    return app


def serve_api(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    """Serve the FastAPI control console API."""

    _uvicorn_server.run(
        "loop_harness.api:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )


def _initial_tokens_from_env() -> list[str]:
    """Read comma-separated API tokens from environment."""

    raw = os.environ.get("LOOPHARNESS_API_TOKENS") or os.environ.get("LOOPHARNESS_API_TOKEN") or ""
    return [token.strip() for token in raw.split(",") if token.strip()]


def _fallback_app(loop_harness: LoopHarness, auth: BearerTokenAuth) -> FallbackApp:
    """Return a fallback route manifest when FastAPI is unavailable."""

    return FallbackApp(
        auth=auth,
        app_state={
            "sqlite_path": str(loop_harness.config.sqlite_path),
            "mode": "fallback",
        },
        routes=[
            {"method": "GET", "path": "/health"},
            {"method": "GET", "path": "/runs"},
            {"method": "GET", "path": "/metrics"},
            {"method": "GET", "path": "/api/health"},
            {"method": "GET", "path": "/api/version"},
            {"method": "GET", "path": "/api/auth/check"},
            {"method": "POST", "path": "/api/evidence/runs"},
            {"method": "GET", "path": "/api/evidence/runs"},
            {"method": "GET", "path": "/api/evidence/runs/{run_id}"},
            {"method": "GET", "path": "/api/evidence/runs/{run_id}/visualization"},
            {"method": "GET", "path": "/api/evidence/runs/{run_id}/report"},
            {"method": "GET", "path": "/api/evidence/runs/{run_id}/graph"},
            {"method": "GET", "path": "/api/evidence/runs/{run_id}/gaps"},
            {"method": "GET", "path": "/api/evidence/runs/{run_id}/nodes/{node_id}"},
            {"method": "GET", "path": "/api/evidence/workflows/{workflow_id}/map"},
            {"method": "GET", "path": "/api/evidence/workflows/{workflow_id}/graph"},
            {"method": "GET", "path": "/api/evidence/workflows/{workflow_id}/charts/optimization"},
            {"method": "POST", "path": "/api/evidence/charts/optimization"},
            {"method": "POST", "path": "/api/evidence/review-packages"},
            {"method": "POST", "path": "/api/evidence/review-packages/validate"},
            {"method": "POST", "path": "/api/evidence/review-packages/submit"},
            {"method": "GET", "path": "/api/evidence/review-packages/{package_id}/decision"},
            {"method": "GET", "path": "/api/evidence/review-decisions"},
            {"method": "POST", "path": "/api/evidence/review-decisions/{decision_id}/approve"},
            {"method": "POST", "path": "/api/evidence/review-decisions/{decision_id}/reject"},
            {"method": "POST", "path": "/api/evidence/import/quant-csv"},
            {"method": "POST", "path": "/api/evidence/workflows/{workflow_id}/baseline"},
            {"method": "GET", "path": "/api/evidence/workflows/{workflow_id}/baseline"},
            {"method": "POST", "path": "/api/evidence/contracts/validate"},
            {"method": "POST", "path": "/api/evidence/boundary/classify"},
            {"method": "POST", "path": "/api/evidence/goals/{scenario_id}"},
            {"method": "GET", "path": "/api/evidence/goals/{scenario_id}"},
            {"method": "GET", "path": "/api/evidence/decision-memory/{scenario_id}"},
            {"method": "POST", "path": "/api/evidence/shadow-queue"},
            {"method": "GET", "path": "/api/evidence/shadow-queue"},
            {"method": "POST", "path": "/api/evidence/compare"},
            {"method": "POST", "path": "/api/evidence/compare/export"},
            {"method": "POST", "path": "/api/evidence/metrics/{scenario_id}"},
            {"method": "GET", "path": "/api/evidence/metrics/{scenario_id}"},
            {"method": "GET", "path": "/api/console/snapshot"},
            {"method": "GET", "path": "/api/approvals"},
            {"method": "GET", "path": "/api/runs"},
            {"method": "GET", "path": "/api/backups"},
            {"method": "GET", "path": "/api/scenarios"},
            {"method": "GET", "path": "/api/adapters"},
            {"method": "GET", "path": "/api/learning/observations"},
            {"method": "GET", "path": "/api/learning/safety-findings"},
            {"method": "GET", "path": "/api/learning/validations"},
            {"method": "GET", "path": "/api/config/versions"},
            {"method": "GET", "path": "/api/agent-configs"},
            {"method": "GET", "path": "/api/external-agents"},
            {"method": "GET", "path": "/api/user-profile"},
            {"method": "POST", "path": "/api/user-profile/suggest"},
            {"method": "GET", "path": "/api/reports/latest"},
            {"method": "GET", "path": "/api/shadows"},
            {"method": "GET", "path": "/api/autonomy/actions"},
            {"method": "GET", "path": "/api/autonomy/queue/status"},
        ],
    )


def _adapter_registry() -> AdapterRegistry:
    """Return built-in adapters for API-triggered scenario runs."""

    registry = AdapterRegistry()
    registry.register(DummyAdapter())
    registry.register(OPCAgentAdapter())
    registry.register(QuantResearchDemoAdapter())
    return registry


def _profile_dir(db_path: Path) -> Path:
    """Return profile directory for API-managed user preferences."""

    configured = os.environ.get("LOOPHARNESS_USER_PROFILE_DIR")
    if configured:
        return Path(configured)
    return db_path.parent / "user"


def _suggested_profile_notes(scenario_id: str | None, comments: list[str]) -> str:
    """Build Hermes-style draft notes from decision comments."""

    scope = scenario_id or "all scenarios"
    lines = [
        "# Suggested Profile Notes",
        "",
        "These notes are Hermes draft material. They are not formal constraints until the human moves selected wording into USER_PROFILE.md.",
        "",
        f"Scope: {scope}",
        "",
        "## Decision Evidence",
    ]
    if comments:
        lines.extend(f"- {comment}" for comment in comments[:20])
    else:
        lines.append("- No decision comments found yet.")
    lines.extend(
        [
            "",
            "## Suggested Interpretation",
            "Review the evidence above and write the final preference manually if it matches your actual methodology.",
            "",
            "Status: pending human review",
        ]
    )
    return "\n".join(lines)


def _scenario_registry(db_path: Path) -> ScenarioRegistry:
    """Load persisted scenarios into an in-memory registry."""

    registry = ScenarioRegistry()
    for scenario in ScenarioStore(db_path).list():
        registry.create(scenario)
    return registry


def _scenario_runner(db_path: Path) -> ScenarioRunner:
    """Build a scenario runner for Web API triggered runs."""

    return ScenarioRunner(
        scenarios=_scenario_registry(db_path),
        adapters=_adapter_registry(),
        raw_logs=RawLogStore(db_path),
        summary_logs=SummaryLogStore(db_path),
    )


def _autonomy_status(status: str) -> Any:
    """Convert an autonomy action status string without importing at module load."""

    from loop_harness.autonomy import AutonomyActionStatus

    return AutonomyActionStatus(status)


def _approval_item(approval_id: str, db_path: Path) -> dict[str, Any] | None:
    """Return one approval item by id."""

    for item in ApprovalInbox(db_path).list_items():
        if item.source_id == approval_id:
            return {**item.model_dump(mode="json"), "detail": _approval_detail(approval_id, db_path)}
    return None


def _approval_detail(approval_id: str, db_path: Path) -> dict[str, Any] | None:
    """Return the full source object behind one approval item."""

    prompt_proposal = PromptProposalStore(db_path).get(approval_id)
    if prompt_proposal is not None:
        return prompt_proposal.model_dump(mode="json")

    generic_proposal = ProposalStore(db_path).get(approval_id)
    if generic_proposal is not None:
        return generic_proposal.model_dump(mode="json")

    recommendation = VersionRecommendationStore(db_path).get(approval_id)
    if recommendation is not None:
        return recommendation.model_dump(mode="json")

    parameter_suggestion = ParameterSuggestionStore(db_path).get(approval_id)
    if parameter_suggestion is not None:
        return parameter_suggestion.model_dump(mode="json")

    review_decision = ReviewPackageDecisionStore(db_path).get(approval_id)
    if review_decision is not None:
        return review_decision.model_dump(mode="json")

    return None


def _required_comment(
    payload: dict[str, Any] | None,
    db_path: Path,
    source_id: str,
    item: dict[str, Any] | None,
) -> str:
    """Extract a required operator comment for destructive or resolving actions."""

    comment = str((payload or {}).get("comment", "")).strip()
    if not comment:
        _record_decision(
            db_path=db_path,
            source_id=source_id,
            source_type=str(item["item_type"]) if item else "approval",
            kind=DecisionKind.ERROR,
            scenario_id=str(item["scenario_id"]) if item else None,
            action="approval_decision",
            comment="Operator comment is required.",
            details={"source_id": source_id},
        )
        from fastapi import HTTPException  # type: ignore[import-not-found]

        raise HTTPException(
            status_code=400,
            detail=_api_error(
                "validation.operator_comment_required",
                "Operator comment is required.",
                {"source_id": source_id},
            ),
        )
    return comment


def _api_error(code: str, message: str, details: dict[str, Any]) -> dict[str, Any]:
    """Return the stable API error envelope."""

    return {"code": code, "message": message, "details": details}


def _record_decision(
    db_path: Path,
    source_id: str,
    source_type: str,
    kind: DecisionKind,
    scenario_id: str | None,
    action: str,
    comment: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Persist an audit record for operator and safety decisions."""

    DecisionLogStore(db_path).record(
        DecisionRecord(
            source_id=source_id,
            source_type=source_type,
            kind=kind,
            scenario_id=scenario_id,
            action=action,
            comment=comment,
            before=before or {},
            after=after or {},
            result=result or {},
            details=details or {},
        )
    )
