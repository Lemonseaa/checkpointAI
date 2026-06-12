import type { CandidateChartPoint, OptimizationChartPayload } from "../../types/api";

type OptimizationChartsProps = {
  chart?: OptimizationChartPayload;
  highlightedRunId?: string;
};

export function OptimizationCharts({ chart, highlightedRunId }: OptimizationChartsProps) {
  if (!chart || chart.candidate_points.length === 0) {
    return (
      <div className="rounded-md border border-border bg-panel p-4 text-sm text-muted">
        Need at least one baseline and one candidate to visualize optimization impact.
      </div>
    );
  }

  const points = chart.candidate_points;
  const violations = points.filter((point) => point.guardrail_status === "violated");
  const best = points.find((point) => point.best_candidate);

  return (
    <div className="space-y-4">
      <div>
        <div className="text-sm font-medium text-ink">Optimization impact chart</div>
        <p className="mt-1 text-sm text-muted">{chart.summary}</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div className="rounded-md border border-border bg-white p-3">
          <ScatterPlot points={points} highlightedRunId={highlightedRunId} />
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <Legend label="Candidate" className="border-blue-200 bg-blue-50 text-blue-700" />
            <Legend label="Best" className="border-emerald-200 bg-emerald-50 text-emerald-700" />
            <Legend label="Guardrail violated" className="border-red-200 bg-red-50 text-red-700" />
            <Legend label="Current run" className="border-violet-200 bg-violet-50 text-violet-700" />
          </div>
        </div>

        <div className="space-y-3">
          <SummaryBox label="Baseline" value={chart.baseline_run_id} />
          <SummaryBox label="Best candidate" value={best?.run_id ?? "none"} />
          <SummaryBox label="Guardrails" value={chart.guardrail_summary} tone={violations.length ? "red" : "green"} />
        </div>
      </div>

      <div className="grid gap-2">
        {points.map((point) => (
          <CandidateRow key={point.run_id} point={point} highlighted={point.run_id === highlightedRunId} />
        ))}
      </div>
    </div>
  );
}

function ScatterPlot({ points, highlightedRunId }: { points: CandidateChartPoint[]; highlightedRunId?: string }) {
  const sharpes = points.map((point) => point.sharpe ?? 0);
  const drawdowns = points.map((point) => point.max_drawdown ?? 0);
  const minSharpe = Math.min(...sharpes, 0);
  const maxSharpe = Math.max(...sharpes, 1);
  const minDrawdown = Math.min(...drawdowns, 0);
  const maxDrawdown = Math.max(...drawdowns, 0.3);
  const width = 520;
  const height = 220;
  const pad = 28;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-64 w-full" role="img" aria-label="Sharpe versus max drawdown chart">
      <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke="#CBD5E1" />
      <line x1={pad} y1={pad} x2={pad} y2={height - pad} stroke="#CBD5E1" />
      <text x={pad} y={18} className="fill-slate-500 text-[10px]">
        Sharpe ↑
      </text>
      <text x={width - 88} y={height - 8} className="fill-slate-500 text-[10px]">
        Max drawdown →
      </text>
      {points.map((point) => {
        const x = scale(point.max_drawdown ?? 0, minDrawdown, maxDrawdown, pad, width - pad);
        const y = scale(point.sharpe ?? 0, minSharpe, maxSharpe, height - pad, pad);
        const violated = point.guardrail_status === "violated";
        const highlighted = point.run_id === highlightedRunId;
        const fill = violated ? "#DC2626" : point.best_candidate ? "#059669" : highlighted ? "#7C3AED" : "#2563EB";
        return (
          <g key={point.run_id}>
            <circle cx={x} cy={y} r={highlighted ? 8 : 6} fill={fill} opacity={0.9} />
            <text x={x + 8} y={y - 6} className="fill-slate-700 text-[9px]">
              {shortRun(point.run_id)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function CandidateRow({ point, highlighted }: { point: CandidateChartPoint; highlighted: boolean }) {
  const tone =
    point.guardrail_status === "violated"
      ? "border-red-200 bg-red-50"
      : point.best_candidate
        ? "border-emerald-200 bg-emerald-50"
        : highlighted
          ? "border-violet-200 bg-violet-50"
          : "border-border bg-panel";
  return (
    <div className={`rounded-md border px-3 py-2 text-sm ${tone}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="font-medium text-ink">{point.run_id}</div>
        <div className="flex flex-wrap gap-2 text-xs">
          {point.best_candidate ? <Badge label="best" tone="green" /> : null}
          {highlighted ? <Badge label="current" tone="violet" /> : null}
          <Badge label={point.guardrail_status} tone={point.guardrail_status === "violated" ? "red" : "green"} />
          <Badge label={point.candidate_quality} tone={point.candidate_quality === "weak" ? "red" : "blue"} />
        </div>
      </div>
      <div className="mt-2 grid gap-2 text-xs text-muted sm:grid-cols-4">
        <span>sharpe: {formatNumber(point.sharpe)}</span>
        <span>max_drawdown: {formatNumber(point.max_drawdown)}</span>
        <span>return: {formatNumber(point.total_return)}</span>
        <span>objective: {formatNumber(point.objective_score)}</span>
      </div>
    </div>
  );
}

function SummaryBox({ label, value, tone = "neutral" }: { label: string; value: string; tone?: "neutral" | "red" | "green" }) {
  const className = {
    neutral: "border-border bg-panel",
    red: "border-red-200 bg-red-50",
    green: "border-emerald-200 bg-emerald-50"
  }[tone];
  return (
    <div className={`rounded-md border p-3 ${className}`}>
      <div className="text-xs font-medium uppercase text-muted">{label}</div>
      <div className="mt-1 text-sm font-medium text-ink">{value}</div>
    </div>
  );
}

function Badge({ label, tone }: { label: string; tone: "blue" | "green" | "red" | "violet" }) {
  const className = {
    blue: "border-blue-200 bg-blue-50 text-blue-700",
    green: "border-emerald-200 bg-emerald-50 text-emerald-700",
    red: "border-red-200 bg-red-50 text-red-700",
    violet: "border-violet-200 bg-violet-50 text-violet-700"
  }[tone];
  return <span className={`rounded border px-2 py-0.5 font-medium ${className}`}>{label}</span>;
}

function Legend({ label, className }: { label: string; className: string }) {
  return <span className={`rounded border px-2 py-0.5 font-medium ${className}`}>{label}</span>;
}

function scale(value: number, min: number, max: number, outMin: number, outMax: number) {
  if (max === min) {
    return (outMin + outMax) / 2;
  }
  return outMin + ((value - min) / (max - min)) * (outMax - outMin);
}

function formatNumber(value?: number | null) {
  if (value === null || value === undefined) {
    return "-";
  }
  return value.toFixed(3);
}

function shortRun(runId: string) {
  if (runId.length <= 10) {
    return runId;
  }
  return `${runId.slice(0, 4)}…${runId.slice(-4)}`;
}
