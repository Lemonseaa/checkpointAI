import type { EvidenceReport } from "../../types/api";

type MetricDelta = {
  name: string;
  value: number;
  category: "business" | "system" | "data_quality";
};

type MetricDeltaChartProps = {
  report?: EvidenceReport;
};

export function MetricDeltaChart({ report }: MetricDeltaChartProps) {
  const rows = metricDeltaRows(report);
  const maxAbsDelta = Math.max(0.001, ...rows.map((row) => Math.abs(row.value)));

  if (!rows.length) {
    return <p className="text-sm text-muted">Run a comparison to see metric deltas.</p>;
  }

  const businessRows = rows.filter((row) => row.category === "business");
  const improvedBusinessMetrics = businessRows.filter((row) => row.value > 0).length;
  const worsenedBusinessMetrics = businessRows.filter((row) => row.value < 0).length;
  const systemRows = rows.filter((row) => row.category === "system");

  return (
    <div className="space-y-3">
      <div className="rounded-md border border-border bg-panel px-3 py-2 text-sm text-ink">
        <div className="font-semibold">Impact Summary</div>
        <div className="mt-1 text-xs text-muted">
          Business metrics improved: {improvedBusinessMetrics}; worsened: {worsenedBusinessMetrics}; system metrics
          tracked: {systemRows.length}.
        </div>
      </div>
      {rows.map((row) => {
        const width = `${Math.max(6, (Math.abs(row.value) / maxAbsDelta) * 100)}%`;
        const color = row.value > 0 ? "bg-emerald-500" : row.value < 0 ? "bg-red-500" : "bg-slate-400";
        return (
          <div key={`${row.category}-${row.name}`}>
            <div className="mb-1 flex items-center justify-between gap-3 text-xs">
              <span className="font-medium text-ink">{row.name}</span>
              <span className="text-muted">
                {row.category} / {formatDelta(row.value)}
              </span>
            </div>
            <div className="h-2 rounded-full bg-border">
              <div className={`h-2 rounded-full ${color}`} style={{ width }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function metricDeltaRows(report?: EvidenceReport): MetricDelta[] {
  const comparison = report?.comparison;
  if (!comparison) {
    return [];
  }
  return [
    ...Object.entries(comparison.business_metric_diffs).map(([name, value]) => ({
      name,
      value,
      category: "business" as const
    })),
    ...Object.entries(comparison.system_metric_diffs).map(([name, value]) => ({
      name,
      value,
      category: "system" as const
    })),
    ...Object.entries(comparison.data_quality_metric_diffs).map(([name, value]) => ({
      name,
      value,
      category: "data_quality" as const
    }))
  ];
}

function formatDelta(value: number) {
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(3)}`;
}
