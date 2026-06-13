import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listEvidenceRuns } from "../../api/client";
import { Card } from "../../components/Card";
import { DataTable } from "../../components/DataTable";
import { EmptyState } from "../../components/EmptyState";
import { MetricGrid } from "../../components/MetricGrid";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { shortId } from "../../lib/format";
import type { StoredEvidenceRun } from "../../types/api";

export function WorkflowListPage() {
  const evidenceRuns = useQuery({ queryKey: ["evidence-runs"], queryFn: () => listEvidenceRuns() });
  const runs = evidenceRuns.data ?? [];
  const workflowGroups = groupByWorkflow(runs);
  const totalBlackBoxes = runs.reduce((sum, item) => sum + item.visualization.black_box_node_ids.length, 0);
  const averageTraceCoverage = average(runs.map((item) => item.visualization.trace_coverage));
  const averageMetricCoverage = average(runs.map((item) => item.visualization.metric_coverage));

  return (
    <>
      <PageHeader
        title="Workflow Maps"
        description="Imported workflow structures, coverage, black-box exposure, and latest evidence runs."
      />

      <MetricGrid
        metrics={[
          { label: "Workflows", value: workflowGroups.length },
          { label: "Evidence Runs", value: runs.length },
          { label: "Avg Trace Coverage", value: runs.length ? `${Math.round(averageTraceCoverage * 100)}%` : "-" },
          { label: "Avg Metric Coverage", value: runs.length ? `${Math.round(averageMetricCoverage * 100)}%` : "-" },
          { label: "Black-Box Nodes", value: totalBlackBoxes }
        ]}
      />

      <div className="mt-5">
        <Card title="Workflow Coverage">
          {workflowGroups.length ? (
            <DataTable<WorkflowGroup>
              rows={workflowGroups}
              columns={[
                { key: "workflow", header: "Workflow", render: (row) => row.workflowId },
                { key: "runs", header: "Runs", render: (row) => row.runs.length },
                {
                  key: "trace",
                  header: "Trace Coverage",
                  render: (row) => `${Math.round(row.averageTraceCoverage * 100)}%`
                },
                {
                  key: "metric",
                  header: "Metric Coverage",
                  render: (row) => `${Math.round(row.averageMetricCoverage * 100)}%`
                },
                { key: "black", header: "Black Boxes", render: (row) => row.blackBoxCount },
                {
                  key: "latest",
                  header: "Latest Run",
                  render: (row) => (
                    <Link className="font-medium text-accent" to={`/evidence/runs/${row.latest.run.run_id}`}>
                      {shortId(row.latest.run.run_id)}
                    </Link>
                  )
                },
                {
                  key: "kind",
                  header: "Latest Kind",
                  render: (row) => <StatusBadge value={row.latest.run.run_kind} />
                },
                {
                  key: "recommendation",
                  header: "Latest Recommendation",
                  render: (row) => <StatusBadge value={row.latest.report.recommendation} />
                }
              ]}
            />
          ) : (
            <EmptyState title="No workflow maps" body="Ingest evidence runs to generate workflow maps." />
          )}
        </Card>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        {workflowGroups.map((group) => (
          <Card key={group.workflowId} title={group.workflowId}>
            <div className="mb-3 flex flex-wrap gap-2">
              <StatusBadge value={group.latest.run.run_kind} />
              <StatusBadge value={group.latest.report.recommendation} />
            </div>
            {isNonDecisionEvidence(group.latest.run.run_kind) ? (
              <div className="mb-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                Fixture or synthetic evidence only validates the harness path; it cannot support optimization claims.
              </div>
            ) : null}
            <div className="text-sm text-ink">
              {group.latest.visualization.nodes.map((node) => node.name || node.id).join(" -> ") || "No nodes"}
            </div>
            <div className="mt-3 grid grid-cols-3 gap-3 text-xs text-muted">
              <div>Trace {Math.round(group.averageTraceCoverage * 100)}%</div>
              <div>Metric {Math.round(group.averageMetricCoverage * 100)}%</div>
              <div>Black boxes {group.blackBoxCount}</div>
            </div>
          </Card>
        ))}
      </div>
    </>
  );
}

type WorkflowGroup = {
  workflowId: string;
  runs: StoredEvidenceRun[];
  latest: StoredEvidenceRun;
  averageTraceCoverage: number;
  averageMetricCoverage: number;
  blackBoxCount: number;
};

function groupByWorkflow(runs: StoredEvidenceRun[]): WorkflowGroup[] {
  const groups = new Map<string, StoredEvidenceRun[]>();
  for (const run of runs) {
    const existing = groups.get(run.run.workflow_id) ?? [];
    existing.push(run);
    groups.set(run.run.workflow_id, existing);
  }
  return [...groups.entries()].map(([workflowId, groupedRuns]) => {
    const latest = groupedRuns[groupedRuns.length - 1];
    return {
      workflowId,
      runs: groupedRuns,
      latest,
      averageTraceCoverage: average(groupedRuns.map((item) => item.visualization.trace_coverage)),
      averageMetricCoverage: average(groupedRuns.map((item) => item.visualization.metric_coverage)),
      blackBoxCount: groupedRuns.reduce((sum, item) => sum + item.visualization.black_box_node_ids.length, 0)
    };
  });
}

function average(values: number[]) {
  if (!values.length) {
    return 0;
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function isNonDecisionEvidence(runKind: string) {
  return runKind === "fixture" || runKind === "synthetic";
}
