import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  compareEvidenceRuns,
  createEvidenceProposal,
  getDecisionMemory,
  getApiErrorMessage,
  getEvidenceBaseline,
  getEvidenceGapReport,
  getNodeEvidenceDetail,
  getOptimizationChart,
  getOptimizationGoal,
  getRunGraph,
  listEvidenceRuns
} from "../../api/client";
import { Card } from "../../components/Card";
import { DataTable } from "../../components/DataTable";
import { EmptyState } from "../../components/EmptyState";
import { MetricGrid } from "../../components/MetricGrid";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { shortId } from "../../lib/format";
import type { StoredEvidenceRun } from "../../types/api";
import { EvidenceQualityPanel } from "./EvidenceQualityPanel";
import { MetricDeltaChart } from "./MetricDeltaChart";
import { NodeInspector } from "./NodeInspector";
import { OptimizationCharts } from "./OptimizationCharts";
import { WorkflowMap } from "./WorkflowMap";

export function EvidencePage() {
  const [selectedRunId, setSelectedRunId] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const [baselineRunId, setBaselineRunId] = useState("");
  const [candidateRunId, setCandidateRunId] = useState("");
  const evidenceRuns = useQuery({ queryKey: ["evidence-runs"], queryFn: () => listEvidenceRuns() });
  const runs = evidenceRuns.data ?? [];
  const selected = runs.find((item) => item.run.run_id === selectedRunId) ?? runs[0];
  const workflowId = selected?.run.workflow_id || runs[0]?.run.workflow_id || "";
  const scenarioId = selected?.run.scenario_id || "default";
  const baseline = useQuery({
    queryKey: ["evidence-baseline", workflowId],
    queryFn: () => getEvidenceBaseline(workflowId),
    enabled: Boolean(workflowId),
    retry: false
  });
  const activeNodeId =
    selected && selected.visualization.nodes.some((node) => node.id === selectedNodeId)
      ? selectedNodeId
      : selected?.visualization.run_path[0] || selected?.visualization.nodes[0]?.id || "";
  const baselineValue = baselineRunId || baseline.data?.baseline_run_id || runs[0]?.run.run_id || "";
  const candidateValue = candidateRunId || runs[1]?.run.run_id || runs[0]?.run.run_id || "";
  const canCompare = Boolean(baselineValue && candidateValue && baselineValue !== candidateValue);
  const compare = useMutation({
    mutationFn: () => compareEvidenceRuns(baselineValue, candidateValue)
  });
  const createProposal = useMutation({
    mutationFn: () => createEvidenceProposal(baselineValue, candidateValue, "quant")
  });
  const nodeDetail = useQuery({
    queryKey: ["evidence-node", selected?.run.run_id, activeNodeId],
    queryFn: () => getNodeEvidenceDetail(selected?.run.run_id ?? "", activeNodeId),
    enabled: Boolean(selected?.run.run_id && activeNodeId),
    retry: false
  });
  const gapReport = useQuery({
    queryKey: ["evidence-gaps", selected?.run.run_id],
    queryFn: () => getEvidenceGapReport(selected?.run.run_id ?? ""),
    enabled: Boolean(selected?.run.run_id),
    retry: false
  });
  const workflowGraph = useQuery({
    queryKey: ["evidence-run-graph", selected?.run.run_id],
    queryFn: () => getRunGraph(selected?.run.run_id ?? ""),
    enabled: Boolean(selected?.run.run_id),
    retry: false
  });
  const optimizationChart = useQuery({
    queryKey: ["optimization-chart", workflowId],
    queryFn: () => getOptimizationChart(workflowId),
    enabled: Boolean(workflowId),
    retry: false
  });
  const goal = useQuery({
    queryKey: ["optimization-goal", scenarioId],
    queryFn: () => getOptimizationGoal(scenarioId),
    enabled: Boolean(selected?.run.scenario_id),
    retry: false
  });
  const decisionMemory = useQuery({
    queryKey: ["decision-memory", scenarioId],
    queryFn: () => getDecisionMemory(scenarioId),
    enabled: Boolean(selected?.run.scenario_id),
    retry: false
  });
  const actionItems = getActionItems(compare.data?.recommendation ?? selected?.report.recommendation, {
    blackBoxCount: compare.data?.black_box_node_ids.length ?? selected?.visualization.black_box_node_ids.length ?? 0,
    metricCoverage: compare.data?.metric_coverage ?? selected?.visualization.metric_coverage ?? 0
  });

  return (
    <>
      <PageHeader
        title="Evidence Runs"
        description="External workflow evidence, visualization coverage, black-box nodes, and baseline-ready reports."
      />

      <MetricGrid
        metrics={[
          { label: "Evidence Runs", value: runs.length },
          {
            label: "Trace Coverage",
            value: selected ? `${Math.round(selected.visualization.trace_coverage * 100)}%` : "-"
          },
          {
            label: "Metric Coverage",
            value: selected ? `${Math.round(selected.visualization.metric_coverage * 100)}%` : "-"
          },
          {
            label: "Black Boxes",
            value: selected ? selected.visualization.black_box_node_ids.length : "-"
          }
        ]}
      />

      <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_440px]">
        <Card title="Evidence Run List">
          {runs.length ? (
            <DataTable<StoredEvidenceRun>
              rows={runs}
              columns={[
                {
                  key: "run",
                  header: "Run",
                  render: (row) => (
                    <button
                      className="font-medium text-accent"
                      onClick={() => {
                        setSelectedRunId(row.run.run_id);
                        setSelectedNodeId(row.visualization.run_path[0] || row.visualization.nodes[0]?.id || "");
                      }}
                    >
                      {shortId(row.run.run_id)}
                    </button>
                  )
                },
                { key: "workflow", header: "Workflow", render: (row) => row.run.workflow_id },
                { key: "kind", header: "Kind", render: (row) => <StatusBadge value={row.run.run_kind} /> },
                {
                  key: "coverage",
                  header: "Coverage",
                  render: (row) =>
                    `${Math.round(row.visualization.trace_coverage * 100)}% trace / ${Math.round(
                      row.visualization.metric_coverage * 100
                    )}% metric`
                },
                {
                  key: "recommendation",
                  header: "Recommendation",
                  render: (row) => <StatusBadge value={row.report.recommendation} />
                },
                {
                  key: "baseline",
                  header: "Baseline",
                  render: (row) =>
                    baseline.data?.baseline_run_id === row.run.run_id ? <StatusBadge value="Active baseline" /> : "-"
                },
                {
                  key: "open",
                  header: "",
                  render: (row) => (
                    <Link className="text-sm font-medium text-accent" to={`/evidence/runs/${row.run.run_id}`}>
                      Open {shortId(row.run.run_id)}
                    </Link>
                  )
                }
              ]}
            />
          ) : (
            <EmptyState
              title="No evidence runs"
              body="Ingest external workflow runs through the Evidence API or CLI to populate this view."
            />
          )}
        </Card>

        <Card title="Workflow Visualization">
          {selected ? (
            <WorkflowMap
              visualization={selected.visualization}
              graph={workflowGraph.data}
              selectedNodeId={activeNodeId}
              onSelectNode={setSelectedNodeId}
            />
          ) : (
            <p className="text-sm text-muted">Select an evidence run to inspect workflow structure.</p>
          )}
        </Card>
      </div>

      <div className="mt-5">
        <Card title="Optimization Charts">
          <OptimizationCharts chart={optimizationChart.data} highlightedRunId={selected?.run.run_id} />
        </Card>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_440px]">
        <Card title="Node Evidence">
          <NodeInspector visualization={selected?.visualization} detail={nodeDetail.data} nodeId={activeNodeId} />
        </Card>

        <div className="space-y-5">
          <Card title="Evidence Quality">
            <EvidenceQualityPanel report={selected?.report} />
          </Card>
          <Card title="What to do next">
            {actionItems.length ? (
              <ul className="space-y-2 text-sm text-ink">
                {actionItems.map((item) => (
                  <li key={item} className="rounded-md border border-border bg-panel px-3 py-2">
                    {item}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted">No immediate action. Keep collecting evidence.</p>
            )}
          </Card>
        </div>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <Card title="Evidence Gaps">
          <p className="text-sm text-ink">{gapReport.data?.summary ?? "Gap report unavailable."}</p>
          <div className="mt-3 space-y-2 text-xs text-muted">
            {(gapReport.data?.gaps ?? []).slice(0, 4).map((gap) => (
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
        </Card>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_440px]">
        <Card title="Baseline vs Candidate">
          <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto] md:items-end">
            <label className="block text-sm font-medium text-ink">
              Baseline run
              <select
                className="mt-1 w-full rounded-md border border-border bg-white px-3 py-2 text-sm text-ink"
                value={baselineValue}
                onChange={(event) => setBaselineRunId(event.target.value)}
              >
                {runs.map((item) => (
                  <option key={item.run.run_id} value={item.run.run_id}>
                    {shortId(item.run.run_id)} / {item.run.workflow_id}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-medium text-ink">
              Candidate run
              <select
                className="mt-1 w-full rounded-md border border-border bg-white px-3 py-2 text-sm text-ink"
                value={candidateValue}
                onChange={(event) => setCandidateRunId(event.target.value)}
              >
                {runs.map((item) => (
                  <option key={item.run.run_id} value={item.run.run_id}>
                    {shortId(item.run.run_id)} / {item.run.workflow_id}
                  </option>
                ))}
              </select>
            </label>
            <button
              className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-border disabled:text-muted"
              disabled={!canCompare || compare.isPending}
              onClick={() => compare.mutate()}
            >
              {compare.isPending ? "Comparing..." : "Compare"}
            </button>
          </div>

          {!runs.length ? (
            <p className="mt-3 text-sm text-muted">Ingest at least two evidence runs to compare optimization impact.</p>
          ) : null}
          {baselineValue && candidateValue && baselineValue === candidateValue ? (
            <p className="mt-3 text-sm text-amber-700">Choose two different runs before comparing.</p>
          ) : null}
          {compare.error ? <p className="mt-3 text-sm text-red-700">{getApiErrorMessage(compare.error)}</p> : null}
          {compare.data ? (
            <div className="mt-4 rounded-md border border-border bg-panel p-3">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge value={compare.data.recommendation} />
                <span className="text-xs text-muted">
                  {shortId(compare.data.baseline_run_id ?? "")} → {shortId(compare.data.candidate_run_id ?? "")}
                </span>
              </div>
              <p className="mt-2 text-sm text-ink">{compare.data.summary}</p>
              {compare.data.recommendation.includes("approve") ? (
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <button
                    className="rounded-md bg-accent px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-border disabled:text-muted"
                    disabled={createProposal.isPending || Boolean(createProposal.data)}
                    onClick={() => createProposal.mutate()}
                  >
                    {createProposal.data ? "Proposal created" : "Create approval proposal"}
                  </button>
                  {createProposal.data ? (
                    <Link className="text-sm font-medium text-accent" to={`/approvals/${createProposal.data.id}`}>
                      Open approval {createProposal.data.id}
                    </Link>
                  ) : null}
                </div>
              ) : null}
              {createProposal.error ? (
                <p className="mt-3 text-sm text-red-700">{getApiErrorMessage(createProposal.error)}</p>
              ) : null}
            </div>
          ) : (
            <p className="mt-4 text-sm text-muted">Run a comparison to see whether the candidate improved the workflow.</p>
          )}
        </Card>

        <Card title="Metric Delta">
          <MetricDeltaChart report={compare.data} />
        </Card>
      </div>
    </>
  );
}

function getActionItems(
  recommendation: string | undefined,
  coverage: { blackBoxCount: number; metricCoverage: number }
) {
  const actions: string[] = [];
  if (recommendation?.includes("approve")) {
    actions.push("Review candidate approval");
  }
  if (coverage.blackBoxCount > 0) {
    actions.push("Add trace coverage before trusting this workflow");
  }
  if (coverage.metricCoverage < 0.8) {
    actions.push("Improve metric capture before optimization");
  }
  return actions;
}
