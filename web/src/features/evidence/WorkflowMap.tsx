import type { WorkflowGraphNode, WorkflowGraphPayload, WorkflowVisualization } from "../../types/api";

type WorkflowMapProps = {
  visualization: WorkflowVisualization;
  graph?: WorkflowGraphPayload;
  selectedNodeId: string;
  onSelectNode: (nodeId: string) => void;
};

export function WorkflowMap({ visualization, graph, selectedNodeId, onSelectNode }: WorkflowMapProps) {
  const path = graph?.run_path.join(" → ") || visualization.run_path.join(" → ") || "-";
  const graphNodes = graph?.nodes ? [...graph.nodes].sort(sortGraphNodes) : [];
  const filterEntries = Object.entries(graph?.filters ?? {}).filter(([, nodeIds]) => nodeIds.length > 0);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <div className="text-xs font-medium uppercase text-muted">Run path</div>
          <p className="mt-1 text-ink">{path}</p>
        </div>
        <div>
          <div className="text-xs font-medium uppercase text-muted">Black boxes</div>
          <p className="mt-1 text-ink">
            {(graph?.filters.black_box ?? visualization.black_box_node_ids).join(", ") || "None"}
          </p>
        </div>
      </div>

      {graph ? (
        <div className="rounded-md border border-border bg-panel p-3 text-sm text-ink">
          <div className="font-medium">Graph evidence</div>
          <p className="mt-1 text-muted">{graph.summary}</p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            {filterEntries.length ? (
              filterEntries.map(([key, nodeIds]) => (
                <span key={key} className="rounded border border-border bg-white px-2 py-0.5 text-muted">
                  {key}: {nodeIds.length}
                </span>
              ))
            ) : (
              <span className="text-muted">No graph filters active.</span>
            )}
          </div>
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2 text-xs">
        <Legend label="Traced" className="border-emerald-200 bg-emerald-50 text-emerald-700" />
        <Legend label="Metric" className="border-blue-200 bg-blue-50 text-blue-700" />
        <Legend label="Black box" className="border-amber-200 bg-amber-50 text-amber-700" />
        <Legend label="Error" className="border-red-200 bg-red-50 text-red-700" />
        {graph ? <Legend label="Optimizable" className="border-violet-200 bg-violet-50 text-violet-700" /> : null}
      </div>

      <div className="flex flex-wrap items-stretch gap-2">
        {graphNodes.length ? graphNodes.map((node, index) => (
          <GraphNodeButton
            key={node.id}
            node={node}
            selected={node.id === selectedNodeId}
            showArrow={index < graphNodes.length - 1}
            onSelectNode={onSelectNode}
          />
        )) : visualization.nodes.map((node, index) => (
          <div key={node.id} className="flex items-center gap-2">
            <button
              className={`min-w-36 rounded-md border p-3 text-left text-sm transition ${
                node.id === selectedNodeId ? "border-accent bg-blue-50" : "border-border bg-white hover:border-accent"
              }`}
              onClick={() => onSelectNode(node.id)}
            >
              <div className="font-semibold text-ink">{node.name || node.id}</div>
              <div className="mt-1 flex flex-wrap gap-1">
                <NodeBadge label={node.type} />
                {visualization.traced_node_ids.includes(node.id) ? <NodeBadge label="Traced" tone="green" /> : null}
                {visualization.metric_node_ids.includes(node.id) ? <NodeBadge label="Metric" tone="blue" /> : null}
                {visualization.black_box_node_ids.includes(node.id) ? <NodeBadge label="Black box" tone="amber" /> : null}
                {visualization.error_node_ids.includes(node.id) ? <NodeBadge label="Error" tone="red" /> : null}
              </div>
            </button>
            {index < visualization.nodes.length - 1 ? <span className="text-muted">→</span> : null}
          </div>
        ))}
      </div>

      {graph ? (
        <div className="grid gap-3 text-sm md:grid-cols-2">
          <div>
            <div className="text-xs font-medium uppercase text-muted">Metric sources</div>
            <div className="mt-2 space-y-1">
              {Object.entries(graph.metric_sources).slice(0, 6).map(([metric, nodeIds]) => (
                <div key={metric} className="flex justify-between gap-3 rounded border border-border bg-panel px-2 py-1">
                  <span className="font-medium text-ink">{metric}</span>
                  <span className="text-muted">{nodeIds.join(", ") || "run-level"}</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <div className="text-xs font-medium uppercase text-muted">Legend</div>
            <div className="mt-2 space-y-1">
              {Object.entries(graph.legend).map(([key, value]) => (
                <div key={key} className="rounded border border-border bg-panel px-2 py-1 text-muted">
                  <span className="font-medium text-ink">{key}</span>: {value}
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function GraphNodeButton({
  node,
  selected,
  showArrow,
  onSelectNode
}: {
  node: WorkflowGraphNode;
  selected: boolean;
  showArrow: boolean;
  onSelectNode: (nodeId: string) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <button
        className={`min-w-40 rounded-md border p-3 text-left text-sm transition ${
          selected ? "border-accent bg-blue-50" : "border-border bg-white hover:border-accent"
        }`}
        onClick={() => onSelectNode(node.id)}
      >
        <div className="font-semibold text-ink">{node.label}</div>
        <div className="mt-1 text-xs text-muted">
          x{node.layout.x} / y{node.layout.y} / {node.status}
        </div>
        <div className="mt-2 flex flex-wrap gap-1">
          <NodeBadge label={node.node_type} />
          {node.metric_names.length ? <NodeBadge label="Metric" tone="blue" /> : null}
          {node.black_box ? <NodeBadge label="Black box" tone="amber" /> : null}
          {node.error ? <NodeBadge label="Error" tone="red" /> : null}
          {node.high_latency ? <NodeBadge label="Slow" tone="amber" /> : null}
          {node.high_cost ? <NodeBadge label="Cost" tone="amber" /> : null}
          {node.optimizable ? <NodeBadge label="Optimizable" tone="violet" /> : null}
        </div>
      </button>
      {showArrow ? <span className="text-muted">→</span> : null}
    </div>
  );
}

type BadgeTone = "neutral" | "green" | "blue" | "amber" | "red" | "violet";

function NodeBadge({ label, tone = "neutral" }: { label: string; tone?: BadgeTone }) {
  const className = {
    neutral: "border-border bg-panel text-muted",
    green: "border-emerald-200 bg-emerald-50 text-emerald-700",
    blue: "border-blue-200 bg-blue-50 text-blue-700",
    amber: "border-amber-200 bg-amber-50 text-amber-700",
    red: "border-red-200 bg-red-50 text-red-700",
    violet: "border-violet-200 bg-violet-50 text-violet-700"
  }[tone];

  return <span className={`rounded border px-1.5 py-0.5 text-xs font-medium ${className}`}>{label}</span>;
}

function Legend({ label, className }: { label: string; className: string }) {
  return <span className={`rounded border px-2 py-0.5 font-medium ${className}`}>{label}</span>;
}

function sortGraphNodes(left: WorkflowGraphNode, right: WorkflowGraphNode) {
  if (left.layout.x !== right.layout.x) {
    return left.layout.x - right.layout.x;
  }
  return left.layout.y - right.layout.y;
}
