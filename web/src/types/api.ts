export type HealthReport = {
  overall_status: string;
  checks?: Array<{ component: string; status: string; message: string }>;
  recommendations?: string[];
};

export type ApiErrorEnvelope = {
  code: string;
  message: string;
  details: Record<string, unknown>;
};

export type ConsoleSnapshot = {
  scope: { scenario_id?: string | null; allow_cross_scenario: boolean; reason?: string | null };
  scenario_count: number;
  active_scenario_count: number;
  archived_scenario_count: number;
  recent_run_count: number;
  failed_run_count: number;
  pending_approval_count: number;
  scenarios: ScenarioSummary[];
  latest_runs: RunSummary[];
  pending_items: ApprovalItem[];
  operator_summary: string;
};

export type ScenarioSummary = {
  scenario_id: string;
  name: string;
  status: string;
  adapter_type: string;
  business_line_id?: string | null;
  domain_tags: string[];
};

export type Scenario = {
  id: string;
  name: string;
  description: string;
  adapter_type: string;
  business_line_id?: string | null;
  status: string;
  metadata: Record<string, unknown>;
  created_at?: string;
};

export type ApprovalItem = {
  id: string;
  scenario_id: string;
  item_type: string;
  source_id: string;
  title: string;
  summary: string;
  status: string;
  recommended_action: string;
  created_at: string;
  detail?: Record<string, unknown> | null;
};

export type RunSummary = {
  run_id: string;
  scenario_id: string;
  task: string;
  status: string;
  value_summary?: string;
  failed_summary?: string;
  metrics: Record<string, unknown>;
  created_at: string;
};

export type RunDetail = {
  run_id: string;
  scenario_id: string;
  task: string;
  status: string;
  metrics: Record<string, unknown>;
  value_summary: string;
  core_questions: Record<string, string>;
};

export type WorkflowNode = {
  id: string;
  name?: string | null;
  type: string;
  metadata: Record<string, unknown>;
};

export type WorkflowEdge = {
  source: string;
  target: string;
  type: string;
  metadata: Record<string, unknown>;
};

export type WorkflowVisualization = {
  workflow_id: string;
  run_id: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  run_path: string[];
  total_nodes: number;
  traced_node_ids: string[];
  metric_node_ids: string[];
  black_box_node_ids: string[];
  error_node_ids: string[];
  trace_coverage: number;
  metric_coverage: number;
  node_costs: Record<string, number>;
  node_latencies_ms: Record<string, number>;
};

export type WorkflowMapSummary = {
  workflow_id: string;
  scenario_id: string;
  latest_run_id: string;
  node_count: number;
  edge_count: number;
  entry_node_ids: string[];
  exit_node_ids: string[];
  observable_node_ids: string[];
  metric_node_ids: string[];
  black_box_node_ids: string[];
  error_node_ids: string[];
  config_surfaces: string[];
  trace_coverage: number;
  metric_coverage: number;
  value_summary: string;
};

export type WorkflowGraphNode = {
  id: string;
  label: string;
  node_type: string;
  status: string;
  layout: { x: number; y: number };
  metric_names: string[];
  artifact_refs: Array<Record<string, unknown>>;
  black_box: boolean;
  error: boolean;
  high_cost: boolean;
  high_latency: boolean;
  optimizable: boolean;
  gaps: EvidenceGap[];
  metadata: Record<string, unknown>;
};

export type WorkflowGraphEdge = {
  source: string;
  target: string;
  edge_type: string;
  active: boolean;
  metadata: Record<string, unknown>;
};

export type WorkflowGraphPayload = {
  workflow_id: string;
  run_id: string;
  scenario_id: string;
  nodes: WorkflowGraphNode[];
  edges: WorkflowGraphEdge[];
  run_path: string[];
  metric_sources: Record<string, string[]>;
  filters: Record<string, string[]>;
  legend: Record<string, string>;
  summary: string;
};

export type CandidateChartPoint = {
  run_id: string;
  scenario_id: string;
  run_kind: string;
  total_return?: number | null;
  sharpe?: number | null;
  max_drawdown?: number | null;
  win_rate?: number | null;
  turnover?: number | null;
  objective_score?: number | null;
  guardrail_status: string;
  candidate_quality: string;
  best_candidate: boolean;
  summary: string;
  metadata: Record<string, unknown>;
};

export type MetricTrendPoint = {
  run_id: string;
  metric: string;
  value: number;
  role: string;
};

export type OptimizationChartPayload = {
  workflow_id: string;
  scenario_id: string;
  baseline_run_id: string;
  baseline_metrics: Record<string, number>;
  candidate_points: CandidateChartPoint[];
  metric_trends: MetricTrendPoint[];
  chart_fields: string[];
  guardrail_summary: string;
  best_candidate_run_id?: string | null;
  summary: string;
};

export type NodeEvidenceDetail = {
  workflow_id: string;
  run_id: string;
  node_id: string;
  name?: string | null;
  type: string;
  status: string;
  input_summary?: string | null;
  output_summary?: string | null;
  metrics: Record<string, number>;
  latency_ms?: number | null;
  cost?: number | null;
  error?: string | null;
  black_box: boolean;
  optimizable: boolean;
  artifact_refs: Array<Record<string, unknown>>;
  gaps: EvidenceGap[];
  metadata: Record<string, unknown>;
};

export type EvidenceGap = {
  code: string;
  severity: string;
  message: string;
  node_id?: string | null;
  details: Record<string, unknown>;
};

export type EvidenceGapReport = {
  workflow_id: string;
  run_id: string;
  status: string;
  gaps: EvidenceGap[];
  black_box_node_ids: string[];
  missing_metric_node_ids: string[];
  missing_trace_node_ids: string[];
  summary: string;
};

export type OptimizationGoalProfile = {
  scenario_id: string;
  primary_metrics: string[];
  guardrail_metrics: string[];
  max_cost_increase: number;
  max_risk_level: string;
  preferences: Record<string, unknown>;
};

export type DecisionMemorySummary = {
  scenario_id: string;
  approved_count: number;
  rejected_count: number;
  approved_patterns: string[];
  rejected_patterns: string[];
  summary: string;
};

export type EvidenceReport = {
  workflow_id: string;
  run_id?: string | null;
  baseline_run_id?: string | null;
  candidate_run_id?: string | null;
  run_kind: string;
  trace_coverage: number;
  metric_coverage: number;
  black_box_node_ids: string[];
  business_metrics: Record<string, number>;
  system_metrics: Record<string, number>;
  data_quality_metrics: Record<string, number>;
  comparison?: ComparisonResult | null;
  recommendation: string;
  summary: string;
  evidence: EvidencePayload;
};

export type EvidencePayload = {
  quality?: EvidenceQuality;
  [key: string]: unknown;
};

export type EvidenceQuality = {
  status: "accepted" | "warning" | "rejected" | string;
  score: number;
  reasons: string[];
};

export type ComparisonResult = {
  metric_diffs: Record<string, number>;
  business_metric_diffs: Record<string, number>;
  system_metric_diffs: Record<string, number>;
  data_quality_metric_diffs: Record<string, number>;
  metric_evaluations: Record<string, unknown>;
  objective_score: number;
  guardrail_violations: string[];
  improved: boolean;
  summary: string;
  run_kind: string;
  provenance: Record<string, unknown>;
};

export type EvidenceRun = {
  workflow_id: string;
  run_id: string;
  scenario_id: string;
  run_kind: string;
  metrics: Record<string, number>;
  metadata: Record<string, unknown>;
};

export type StoredEvidenceRun = {
  run: EvidenceRun;
  visualization: WorkflowVisualization;
  report: EvidenceReport;
};

export type EvidenceBaseline = {
  workflow_id: string;
  baseline_run_id: string;
  reason: string;
  created_at?: string | null;
};

export type EvidenceProposal = {
  id: string;
  scenario_id: string;
  proposal_kind: string;
  target_type: string;
  target_id: string;
  reason: string;
  expected_metric: string;
  status: string;
  metadata: Record<string, unknown>;
};

export type EvidenceReviewPackage = {
  package_id: string;
  workflow_id: string;
  scenario_id: string;
  baseline_run_id: string;
  candidate_run_ids: string[];
  graph: WorkflowGraphPayload;
  chart: OptimizationChartPayload;
  comparison_reports: EvidenceReport[];
  gap_summary: string;
  recommended_action: string;
  markdown: string;
  metadata: Record<string, unknown>;
};

export type ReplayValidationResult = {
  package_id: string;
  valid: boolean;
  missing_run_ids: string[];
  drifted_run_ids: string[];
  summary: string;
};

export type ReviewDecisionStatus = "pending" | "approved" | "rejected" | string;

export type ReviewPackageDecision = {
  decision_id: string;
  package_id: string;
  scenario_id: string;
  workflow_id: string;
  baseline_run_id: string;
  candidate_run_ids: string[];
  recommended_action: string;
  status: ReviewDecisionStatus;
  reason: string;
  approval_required: boolean;
  comment?: string | null;
  created_at: string;
  decided_at?: string | null;
  metadata: Record<string, unknown>;
};

export type AdapterDescription = {
  name: string;
  supported_task_types: string[];
  capabilities: Record<string, unknown>;
};

export type BackupRecord = {
  id: string;
  label: string;
  path: string;
  created_at: string;
};

export type RestoreResult = {
  id: string;
  restored: boolean;
  pre_restore_backup_id?: string | null;
};

export type TriggerRunPayload = {
  scenario_id: string;
  task: string;
  context: Record<string, unknown>;
  config?: Record<string, unknown>;
};

export type TriggerRunResult = {
  scenario_id: string;
  run_id: string;
  task: string;
  status: string;
  metrics: Record<string, unknown>;
  value_summary: string;
  answer: string;
};

export type ReportResponse = {
  report: string;
};

export type ShadowResult = {
  id: string;
  proposal_id: string;
  scenario_id: string;
  agent_id: string;
  run_id: string;
  is_shadow: boolean;
  status: string;
  passed: boolean;
  answer: string;
  value_summary: string;
  baseline_metrics: Record<string, unknown>;
  shadow_metrics: Record<string, unknown>;
  metric_diff: Record<string, number>;
  business_metric_diff: Record<string, number>;
  run_kind: string;
  provenance: Record<string, unknown>;
  error_type?: string | null;
  created_at: string;
};

export type TriggerShadowPayload = {
  proposal_id: string;
  task: string;
  context: Record<string, unknown>;
  config?: Record<string, unknown>;
};

export type AutonomyAction = {
  id: string;
  scenario_id: string;
  proposal_id: string;
  action_type: string;
  checkpoint_id: string;
  reason: string;
  status: string;
  result: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AutonomyQueueStatus = {
  paused: boolean;
  pending_count: number;
  running_count: number;
};

export type ProcessAutonomyActionResult = {
  paused: boolean;
  action: AutonomyAction | null;
};

export type LearningObservation = {
  id: string;
  business_line_id: string;
  scenario_id: string;
  observation_type: string;
  severity: string;
  title: string;
  summary: string;
  source_ids: string[];
  created_at: string;
  metadata: Record<string, unknown>;
};

export type SafetyFinding = {
  id: string;
  business_line_id: string;
  scenario_id: string;
  proposal_id: string;
  severity: string;
  reason: string;
  created_at: string;
};

export type ValidationSummary = {
  id: string;
  business_line_id: string;
  scenario_id: string;
  proposal_id: string;
  improved: boolean;
  summary: string;
  metric_diffs: Record<string, number>;
  recommendation: string;
  created_at: string;
};

export type ConfigVersion = {
  id: string;
  business_line_id: string;
  scenario_id: string;
  config: Record<string, unknown>;
  reason: string;
  locked: boolean;
  locked_reason?: string | null;
  created_at: string;
};

export type AgentConfig = {
  id: string;
  business_line_id: string;
  role: string;
  config_version_id: string;
  skills: string[];
  tools: string[];
  mcp_servers: string[];
  triggers: string[];
  constraints: string[];
  model: string;
};

export type ExternalAgentConnection = {
  id: string;
  business_line_id: string;
  scenario_id: string;
  name: string;
  adapter_type: string;
  config: Record<string, unknown>;
  capabilities: Record<string, unknown>;
  active: boolean;
};

export type UserProfilePayload = {
  formal_profile: string;
  suggested_notes: string;
  versions: Array<{ id: string; actor: string; reason: string; created_at: string }>;
};

export type SuggestedProfileNotes = {
  id: string;
  actor: string;
  content: string;
  created_at: string;
  metadata: Record<string, unknown>;
};
