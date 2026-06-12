import axios from "axios";
import type {
  AdapterDescription,
  ApiErrorEnvelope,
  ApprovalItem,
  AutonomyAction,
  AutonomyQueueStatus,
  BackupRecord,
  AgentConfig,
  ConsoleSnapshot,
  ConfigVersion,
  EvidenceReport,
  EvidenceBaseline,
  EvidenceProposal,
  EvidenceGapReport,
  ExternalAgentConnection,
  HealthReport,
  LearningObservation,
  DecisionMemorySummary,
  NodeEvidenceDetail,
  OptimizationChartPayload,
  OptimizationGoalProfile,
  ProcessAutonomyActionResult,
  ReportResponse,
  RestoreResult,
  RunDetail,
  RunSummary,
  SafetyFinding,
  Scenario,
  ShadowResult,
  TriggerShadowPayload,
  TriggerRunPayload,
  TriggerRunResult,
  UserProfilePayload,
  ValidationSummary,
  StoredEvidenceRun,
  WorkflowGraphPayload,
  WorkflowMapSummary,
  WorkflowVisualization
} from "../types/api";

const api = axios.create({
  baseURL: import.meta.env.VITE_CHECKPOINT_API_BASE_URL ?? ""
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("loopharness.token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function setApiToken(token: string) {
  localStorage.setItem("loopharness.token", token);
}

export function getApiToken() {
  return localStorage.getItem("loopharness.token") ?? "";
}

export function getApiErrorMessage(error: unknown) {
  if (axios.isAxiosError<ApiErrorEnvelope>(error)) {
    const data = error.response?.data;
    if (data?.message) {
      return data.message;
    }
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Request failed.";
}

export async function getSnapshot(scenarioId?: string) {
  const response = await api.get<ConsoleSnapshot>("/api/console/snapshot", {
    params: scenarioId ? { scenario_id: scenarioId } : { all_scenarios: true, reason: "web-console" }
  });
  return response.data;
}

export async function getHealth() {
  const response = await api.get<HealthReport>("/api/health");
  return response.data;
}

export async function listApprovals(scenarioId?: string) {
  const response = await api.get<ApprovalItem[]>("/api/approvals", {
    params: scenarioId ? { scenario_id: scenarioId } : undefined
  });
  return response.data;
}

export async function getApproval(id: string) {
  const response = await api.get<ApprovalItem>(`/api/approvals/${id}`);
  return response.data;
}

export async function approveItem(id: string, comment: string) {
  const response = await api.post<{ id: string; updated: boolean }>(`/api/approvals/${id}/approve`, {
    comment
  });
  return response.data;
}

export async function rejectItem(id: string, comment: string) {
  const response = await api.post<{ id: string; updated: boolean }>(`/api/approvals/${id}/reject`, {
    comment
  });
  return response.data;
}

export async function listRuns(scenarioId?: string) {
  const response = await api.get<RunSummary[]>("/api/runs", {
    params: scenarioId ? { scenario_id: scenarioId } : undefined
  });
  return response.data;
}

export async function getRun(id: string) {
  const response = await api.get<RunDetail>(`/api/runs/${id}`);
  return response.data;
}

export async function listEvidenceRuns(workflowId?: string) {
  const response = await api.get<StoredEvidenceRun[]>("/api/evidence/runs", {
    params: workflowId ? { workflow_id: workflowId } : undefined
  });
  return response.data;
}

export async function getEvidenceRun(runId: string) {
  const response = await api.get<StoredEvidenceRun>(`/api/evidence/runs/${runId}`);
  return response.data;
}

export async function getEvidenceVisualization(runId: string) {
  const response = await api.get<WorkflowVisualization>(`/api/evidence/runs/${runId}/visualization`);
  return response.data;
}

export async function getEvidenceReport(runId: string) {
  const response = await api.get<EvidenceReport>(`/api/evidence/runs/${runId}/report`);
  return response.data;
}

export async function getWorkflowMap(workflowId: string) {
  const response = await api.get<WorkflowMapSummary>(`/api/evidence/workflows/${workflowId}/map`);
  return response.data;
}

export async function getWorkflowGraph(workflowId: string) {
  const response = await api.get<WorkflowGraphPayload>(`/api/evidence/workflows/${workflowId}/graph`);
  return response.data;
}

export async function getRunGraph(runId: string) {
  const response = await api.get<WorkflowGraphPayload>(`/api/evidence/runs/${runId}/graph`);
  return response.data;
}

export async function getOptimizationChart(workflowId: string) {
  const response = await api.get<OptimizationChartPayload>(
    `/api/evidence/workflows/${workflowId}/charts/optimization`
  );
  return response.data;
}

export async function buildOptimizationChart(baselineRunId: string, candidateRunIds: string[]) {
  const response = await api.post<OptimizationChartPayload>("/api/evidence/charts/optimization", {
    baseline_run_id: baselineRunId,
    candidate_run_ids: candidateRunIds
  });
  return response.data;
}

export async function getEvidenceGapReport(runId: string) {
  const response = await api.get<EvidenceGapReport>(`/api/evidence/runs/${runId}/gaps`);
  return response.data;
}

export async function getNodeEvidenceDetail(runId: string, nodeId: string) {
  const response = await api.get<NodeEvidenceDetail>(`/api/evidence/runs/${runId}/nodes/${nodeId}`);
  return response.data;
}

export async function getOptimizationGoal(scenarioId: string) {
  const response = await api.get<OptimizationGoalProfile>(`/api/evidence/goals/${scenarioId}`);
  return response.data;
}

export async function saveOptimizationGoal(scenarioId: string, payload: Omit<OptimizationGoalProfile, "scenario_id">) {
  const response = await api.post<OptimizationGoalProfile>(`/api/evidence/goals/${scenarioId}`, payload);
  return response.data;
}

export async function getDecisionMemory(scenarioId: string) {
  const response = await api.get<DecisionMemorySummary>(`/api/evidence/decision-memory/${scenarioId}`);
  return response.data;
}

export async function compareEvidenceRuns(baselineRunId: string, candidateRunId: string) {
  const response = await api.post<EvidenceReport>("/api/evidence/compare", {
    baseline_run_id: baselineRunId,
    candidate_run_id: candidateRunId
  });
  return response.data;
}

export async function getEvidenceBaseline(workflowId: string) {
  const response = await api.get<EvidenceBaseline>(`/api/evidence/workflows/${workflowId}/baseline`);
  return response.data;
}

export async function setEvidenceBaseline(workflowId: string, baselineRunId: string, reason: string) {
  const response = await api.post<EvidenceBaseline>(`/api/evidence/workflows/${workflowId}/baseline`, {
    baseline_run_id: baselineRunId,
    reason
  });
  return response.data;
}

export async function createEvidenceProposal(
  baselineRunId: string,
  candidateRunId: string,
  scenarioId = "evidence"
) {
  const response = await api.post<EvidenceProposal>("/api/evidence/proposals", {
    baseline_run_id: baselineRunId,
    candidate_run_id: candidateRunId,
    scenario_id: scenarioId
  });
  return response.data;
}

export async function triggerRun(payload: TriggerRunPayload) {
  const response = await api.post<TriggerRunResult>("/api/runs", payload);
  return response.data;
}

export async function listBackups() {
  const response = await api.get<BackupRecord[]>("/api/backups");
  return response.data;
}

export async function createBackup(label: string) {
  const response = await api.post<BackupRecord>("/api/backups", { label });
  return response.data;
}

export async function restoreBackup(id: string) {
  const response = await api.post<RestoreResult>(`/api/backups/${id}/restore`, { confirm: "RESTORE" });
  return response.data;
}

export async function listScenarios() {
  const response = await api.get<Scenario[]>("/api/scenarios");
  return response.data;
}

export async function archiveScenario(id: string, reason: string) {
  const response = await api.post<{ id: string; archived: boolean }>(`/api/scenarios/${id}/archive`, {
    reason
  });
  return response.data;
}

export async function listAdapters() {
  const response = await api.get<AdapterDescription[]>("/api/adapters");
  return response.data;
}

export async function getLatestReport(scenarioId?: string) {
  const response = await api.get<ReportResponse>("/api/reports/latest", {
    params: scenarioId ? { scenario_id: scenarioId } : undefined
  });
  return response.data;
}

export async function getRunReport(runId: string) {
  const response = await api.get<ReportResponse>(`/api/reports/runs/${runId}`);
  return response.data;
}

export async function getProposalReport(proposalId: string) {
  const response = await api.get<ReportResponse>(`/api/reports/proposals/${proposalId}`);
  return response.data;
}

export async function listShadows(scenarioId?: string) {
  const response = await api.get<ShadowResult[]>("/api/shadows", {
    params: scenarioId ? { scenario_id: scenarioId } : undefined
  });
  return response.data;
}

export async function getShadow(id: string) {
  const response = await api.get<ShadowResult>(`/api/shadows/${id}`);
  return response.data;
}

export async function triggerShadow(payload: TriggerShadowPayload) {
  const response = await api.post<ShadowResult>("/api/shadows", payload);
  return response.data;
}

export async function listAutonomyActions(scenarioId?: string) {
  const response = await api.get<AutonomyAction[]>("/api/autonomy/actions", {
    params: scenarioId ? { scenario_id: scenarioId } : undefined
  });
  return response.data;
}

export async function getAutonomyQueueStatus() {
  const response = await api.get<AutonomyQueueStatus>("/api/autonomy/queue/status");
  return response.data;
}

export async function pauseAutonomyQueue() {
  const response = await api.post<AutonomyQueueStatus>("/api/autonomy/queue/pause");
  return response.data;
}

export async function resumeAutonomyQueue() {
  const response = await api.post<AutonomyQueueStatus>("/api/autonomy/queue/resume");
  return response.data;
}

export async function processAutonomyAction(actionId: string) {
  const response = await api.post<ProcessAutonomyActionResult>(`/api/autonomy/actions/${actionId}/process`);
  return response.data;
}

export async function listLearningObservations() {
  const response = await api.get<LearningObservation[]>("/api/learning/observations");
  return response.data;
}

export async function listSafetyFindings() {
  const response = await api.get<SafetyFinding[]>("/api/learning/safety-findings");
  return response.data;
}

export async function listValidationSummaries() {
  const response = await api.get<ValidationSummary[]>("/api/learning/validations");
  return response.data;
}

export async function listConfigVersions() {
  const response = await api.get<ConfigVersion[]>("/api/config/versions");
  return response.data;
}

export async function listAgentConfigs() {
  const response = await api.get<AgentConfig[]>("/api/agent-configs");
  return response.data;
}

export async function listExternalAgents() {
  const response = await api.get<ExternalAgentConnection[]>("/api/external-agents");
  return response.data;
}

export async function getUserProfile() {
  const response = await api.get<UserProfilePayload>("/api/user-profile");
  return response.data;
}
