import { JsonBlock } from "../../components/JsonBlock";
import type { NodeEvidenceDetail, WorkflowVisualization } from "../../types/api";

type NodeInspectorProps = {
  visualization?: WorkflowVisualization;
  detail?: NodeEvidenceDetail;
  nodeId: string;
};

export function NodeInspector({ visualization, detail, nodeId }: NodeInspectorProps) {
  const node = visualization?.nodes.find((item) => item.id === nodeId);

  if (!visualization || !node) {
    return <p className="text-sm text-muted">Select a workflow node to inspect evidence.</p>;
  }

  const traced = detail ? detail.status !== "unobserved" : visualization.traced_node_ids.includes(node.id);
  const metricCaptured = detail ? Object.keys(detail.metrics).length > 0 : visualization.metric_node_ids.includes(node.id);
  const blackBox = detail ? detail.black_box : visualization.black_box_node_ids.includes(node.id);
  const error = detail ? Boolean(detail.error) : visualization.error_node_ids.includes(node.id);
  const latency = detail?.latency_ms ?? visualization.node_latencies_ms[node.id];
  const cost = detail?.cost ?? visualization.node_costs[node.id];

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 text-sm">
        <Detail label="Node id" value={node.id} />
        <Detail label="Type" value={node.type} />
        <Detail label="Status" value={detail?.status ?? (traced ? "traced" : "unobserved")} />
        <Detail label="Optimizable" value={detail?.optimizable ? "yes" : "no"} />
        <Detail label="Latency" value={latency === undefined ? "-" : `${latency} ms`} />
        <Detail label="Cost" value={cost === undefined ? "-" : `$${cost.toFixed(3)}`} />
      </div>

      <div className="flex flex-wrap gap-2 text-xs">
        <Status label={traced ? "Traced" : "Trace missing"} tone={traced ? "green" : "amber"} />
        <Status label={metricCaptured ? "Metric captured" : "Metric missing"} tone={metricCaptured ? "blue" : "amber"} />
        {blackBox ? <Status label="Black-box node" tone="amber" /> : null}
        {error ? <Status label="Error node" tone="red" /> : null}
      </div>

      {detail?.input_summary || detail?.output_summary ? (
        <div className="grid gap-3 text-sm md:grid-cols-2">
          <Detail label="Input" value={detail.input_summary ?? "-"} />
          <Detail label="Output" value={detail.output_summary ?? "-"} />
        </div>
      ) : null}

      {detail && Object.keys(detail.metrics).length ? (
        <div>
          <div className="text-xs font-medium uppercase text-muted">Node metrics</div>
          <div className="mt-2">
            <JsonBlock value={detail.metrics} />
          </div>
        </div>
      ) : null}

      {detail?.gaps?.length ? (
        <div>
          <div className="text-xs font-medium uppercase text-muted">Evidence gaps</div>
          <div className="mt-2 space-y-2">
            {detail.gaps.map((gap) => (
              <div key={`${gap.code}-${gap.message}`} className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm">
                <div className="font-medium text-amber-800">{gap.code}</div>
                <div className="mt-1 text-amber-700">{gap.message}</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {detail?.artifact_refs?.length ? (
        <div>
          <div className="text-xs font-medium uppercase text-muted">Artifacts</div>
          <div className="mt-2">
            <JsonBlock value={detail.artifact_refs} />
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs font-medium uppercase text-muted">{label}</div>
      <p className="mt-1 text-ink">{value}</p>
    </div>
  );
}

function Status({ label, tone }: { label: string; tone: "green" | "blue" | "amber" | "red" }) {
  const className = {
    green: "border-emerald-200 bg-emerald-50 text-emerald-700",
    blue: "border-blue-200 bg-blue-50 text-blue-700",
    amber: "border-amber-200 bg-amber-50 text-amber-700",
    red: "border-red-200 bg-red-50 text-red-700"
  }[tone];

  return <span className={`rounded border px-2 py-0.5 font-medium ${className}`}>{label}</span>;
}
