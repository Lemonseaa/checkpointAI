import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { getOptimizationChart, listEvidenceRuns } from "../../api/client";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { MetricGrid } from "../../components/MetricGrid";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { OptimizationCharts } from "./OptimizationCharts";

export function ChartsPage() {
  const evidenceRuns = useQuery({ queryKey: ["evidence-runs"], queryFn: () => listEvidenceRuns() });
  const workflows = useMemo(() => {
    const seen = new Set<string>();
    return (evidenceRuns.data ?? [])
      .map((item) => item.run.workflow_id)
      .filter((workflowId) => {
        if (seen.has(workflowId)) {
          return false;
        }
        seen.add(workflowId);
        return true;
      });
  }, [evidenceRuns.data]);
  const [selectedWorkflow, setSelectedWorkflow] = useState("");
  const workflowId = selectedWorkflow || workflows[0] || "";
  const chart = useQuery({
    queryKey: ["optimization-chart", workflowId],
    queryFn: () => getOptimizationChart(workflowId),
    enabled: Boolean(workflowId),
    retry: false
  });

  return (
    <>
      <PageHeader
        title="Optimization Charts"
        description="Visual proof of baseline, candidates, guardrails, weak runs, and optimization movement."
      />

      <MetricGrid
        metrics={[
          { label: "Workflows", value: workflows.length },
          { label: "Candidates", value: chart.data?.candidate_points.length ?? "-" },
          { label: "Best Candidate", value: chart.data?.best_candidate_run_id ?? "-" },
          { label: "Scenario", value: chart.data?.scenario_id ?? "-" }
        ]}
      />

      <div className="mt-5 grid gap-5 xl:grid-cols-[320px_1fr]">
        <Card title="Workflow">
          {workflows.length ? (
            <div className="space-y-2">
              {workflows.map((item) => (
                <button
                  key={item}
                  className={`w-full rounded-md border px-3 py-2 text-left text-sm transition ${
                    item === workflowId ? "border-accent bg-blue-50" : "border-border bg-white hover:border-accent"
                  }`}
                  onClick={() => setSelectedWorkflow(item)}
                >
                  <div className="font-medium text-ink">{item}</div>
                  {item === workflowId ? <StatusBadge value="selected" /> : null}
                </button>
              ))}
            </div>
          ) : (
            <EmptyState title="No chartable workflows" body="Ingest evidence runs before opening optimization charts." />
          )}
        </Card>

        <Card title="Optimization Impact">
          {workflowId ? (
            <OptimizationCharts chart={chart.data} />
          ) : (
            <EmptyState title="No workflow selected" body="Select a workflow to render baseline and candidate charts." />
          )}
        </Card>
      </div>
    </>
  );
}
