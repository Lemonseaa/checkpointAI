import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useState } from "react";
import {
  getDecisionMemory,
  getEvidenceBaseline,
  getEvidenceGapReport,
  getEvidenceRun,
  getNodeEvidenceDetail,
  getOptimizationChart,
  getOptimizationGoal,
  getRunGraph,
  setEvidenceBaseline
} from "../../api/client";
import { Card } from "../../components/Card";
import { MetricGrid } from "../../components/MetricGrid";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { EvidenceQualityPanel } from "./EvidenceQualityPanel";
import { NodeInspector } from "./NodeInspector";
import { OptimizationCharts } from "./OptimizationCharts";
import { WorkflowMap } from "./WorkflowMap";

export function EvidenceRunDetailPage() {
  const { runId = "" } = useParams();
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const queryClient = useQueryClient();
  const evidenceRun = useQuery({
    queryKey: ["evidence-run", runId],
    queryFn: () => getEvidenceRun(runId),
    enabled: Boolean(runId)
  });
  const stored = evidenceRun.data;
  const workflowId = stored?.run.workflow_id || "";
  const scenarioId = stored?.run.scenario_id || "default";
  const baseline = useQuery({
    queryKey: ["evidence-baseline", workflowId],
    queryFn: () => getEvidenceBaseline(workflowId),
    enabled: Boolean(workflowId),
    retry: false
  });
  const setBaseline = useMutation({
    mutationFn: () => setEvidenceBaseline(workflowId, runId, "Pinned from Evidence Run Detail."),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["evidence-baseline", workflowId] });
    }
  });
  const isActiveBaseline = baseline.data?.baseline_run_id === runId;
  const activeNodeId =
    stored && stored.visualization.nodes.some((node) => node.id === selectedNodeId)
      ? selectedNodeId
      : stored?.visualization.run_path[0] || stored?.visualization.nodes[0]?.id || "";
  const gapReport = useQuery({
    queryKey: ["evidence-gaps", runId],
    queryFn: () => getEvidenceGapReport(runId),
    enabled: Boolean(runId),
    retry: false
  });
  const workflowGraph = useQuery({
    queryKey: ["evidence-run-graph", runId],
    queryFn: () => getRunGraph(runId),
    enabled: Boolean(runId),
    retry: false
  });
  const optimizationChart = useQuery({
    queryKey: ["optimization-chart", workflowId],
    queryFn: () => getOptimizationChart(workflowId),
    enabled: Boolean(workflowId),
    retry: false
  });
  const nodeDetail = useQuery({
    queryKey: ["evidence-node", runId, activeNodeId],
    queryFn: () => getNodeEvidenceDetail(runId, activeNodeId),
    enabled: Boolean(runId && activeNodeId),
    retry: false
  });
  const goal = useQuery({
    queryKey: ["optimization-goal", scenarioId],
    queryFn: () => getOptimizationGoal(scenarioId),
    enabled: Boolean(stored?.run.scenario_id),
    retry: false
  });
  const decisionMemory = useQuery({
    queryKey: ["decision-memory", scenarioId],
    queryFn: () => getDecisionMemory(scenarioId),
    enabled: Boolean(stored?.run.scenario_id),
    retry: false
  });

  return (
    <>
      <PageHeader
        title="Evidence Run Detail"
        description="Node-level evidence, workflow path, report summary, and coverage for one external workflow run."
      />

      <div className="mb-5">
        <Link className="rounded-md border border-border px-3 py-2 text-sm font-medium text-ink" to="/evidence">
          Back to evidence
        </Link>
      </div>

      {stored ? (
        <>
          <MetricGrid
            metrics={[
              { label: "Run", value: stored.run.run_id },
              { label: "Workflow", value: stored.run.workflow_id },
              { label: "Trace Coverage", value: `${Math.round(stored.visualization.trace_coverage * 100)}%` },
              { label: "Metric Coverage", value: `${Math.round(stored.visualization.metric_coverage * 100)}%` }
            ]}
          />

          <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_440px]">
            <Card
              title="Workflow Visualization"
              action={
                <div className="flex flex-wrap items-center gap-2">
                  {isActiveBaseline ? <StatusBadge value="Active baseline" /> : null}
                  <StatusBadge value={stored.report.recommendation} />
                </div>
              }
            >
              <WorkflowMap
                visualization={stored.visualization}
                graph={workflowGraph.data}
                selectedNodeId={activeNodeId}
                onSelectNode={setSelectedNodeId}
              />
            </Card>

            <Card title="Run Report">
              <p className="text-sm text-ink">{stored.report.summary}</p>
              <div className="mt-3 text-xs text-muted">
                Kind: {stored.run.run_kind} / Black boxes: {stored.visualization.black_box_node_ids.length}
              </div>
              <button
                className="mt-4 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-border disabled:text-muted"
                disabled={setBaseline.isPending || isActiveBaseline}
                onClick={() => setBaseline.mutate()}
              >
                {isActiveBaseline ? "Active baseline" : "Set as baseline"}
              </button>
            </Card>
          </div>

          <div className="mt-5">
            <Card title="Optimization Charts">
              <OptimizationCharts chart={optimizationChart.data} highlightedRunId={runId} />
            </Card>
          </div>

          <div className="mt-5">
            <div className="grid gap-5 xl:grid-cols-[1fr_440px]">
              <Card title="Node Evidence">
                <NodeInspector visualization={stored.visualization} detail={nodeDetail.data} nodeId={activeNodeId} />
              </Card>
              <Card title="Evidence Quality">
                <EvidenceQualityPanel report={stored.report} />
              </Card>
            </div>
          </div>

          <div className="mt-5 grid gap-5 xl:grid-cols-3">
            <Card title="Evidence Gaps">
              <p className="text-sm text-ink">{gapReport.data?.summary ?? "Gap report unavailable."}</p>
              <div className="mt-3 space-y-2 text-xs text-muted">
                {(gapReport.data?.gaps ?? []).slice(0, 5).map((gap) => (
                  <div key={`${gap.code}-${gap.node_id ?? gap.message}`} className="rounded border border-border p-2">
                    <span className="font-medium text-ink">{gap.severity}</span> / {gap.code}: {gap.message}
                  </div>
                ))}
              </div>
            </Card>
            <Card title="Optimization Goal">
              {goal.data ? (
                <div className="space-y-2 text-sm">
                  <div>Primary: {goal.data.primary_metrics.join(", ") || "-"}</div>
                  <div>Guardrails: {goal.data.guardrail_metrics.join(", ") || "-"}</div>
                  <div>Max cost increase: {Math.round(goal.data.max_cost_increase * 100)}%</div>
                  <div>Risk level: {goal.data.max_risk_level}</div>
                </div>
              ) : (
                <p className="text-sm text-muted">No human-owned optimization goal profile is configured.</p>
              )}
            </Card>
            <Card title="Decision Memory">
              <p className="text-sm text-ink">
                {decisionMemory.data?.summary ?? "No decision memory has been recorded for this scenario yet."}
              </p>
              {decisionMemory.data ? (
                <div className="mt-3 text-xs text-muted">
                  Approved patterns: {decisionMemory.data.approved_patterns.join(", ") || "-"}
                </div>
              ) : null}
            </Card>
          </div>
        </>
      ) : (
        <Card title="Evidence run unavailable">
          <p className="text-sm text-muted">
            {evidenceRun.isError ? "This evidence run could not be loaded." : "Loading evidence run..."}
          </p>
        </Card>
      )}
    </>
  );
}
