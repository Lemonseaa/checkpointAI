import { expect, test } from "@playwright/test";

const evidenceRuns = [
  {
    run: {
      workflow_id: "quant-demo",
      run_id: "baseline-run-001",
      scenario_id: "quant",
      run_kind: "historical",
      metrics: { sharpe: 0.82, max_drawdown: 0.18, latency_ms: 120 },
      metadata: { strategy: "baseline" }
    },
    visualization: {
      workflow_id: "quant-demo",
      run_id: "baseline-run-001",
      nodes: [
        { id: "data", name: "Load data", type: "tool", metadata: { traced: true } },
        { id: "agent", name: "Strategy agent", type: "agent", metadata: { traced: true } }
      ],
      edges: [{ source: "data", target: "agent", type: "sequence", metadata: {} }],
      run_path: ["data", "agent"],
      total_nodes: 2,
      traced_node_ids: ["data", "agent"],
      metric_node_ids: ["agent"],
      black_box_node_ids: [],
      error_node_ids: [],
      trace_coverage: 1,
      metric_coverage: 0.5,
      node_costs: { agent: 0.12 },
      node_latencies_ms: { data: 20, agent: 100 }
    },
    report: {
      workflow_id: "quant-demo",
      run_id: "baseline-run-001",
      baseline_run_id: null,
      candidate_run_id: null,
      run_kind: "historical",
      trace_coverage: 1,
      metric_coverage: 0.5,
      black_box_node_ids: [],
      business_metrics: { sharpe: 0.82, max_drawdown: 0.18 },
      system_metrics: { latency_ms: 120 },
      data_quality_metrics: { sample_count: 120 },
      comparison: null,
      recommendation: "baseline_ready",
      summary: "Baseline strategy has enough trace coverage for comparison.",
      evidence: { quality: { status: "accepted", score: 1, reasons: [] } }
    }
  },
  {
    run: {
      workflow_id: "quant-demo",
      run_id: "candidate-run-002",
      scenario_id: "quant",
      run_kind: "historical",
      metrics: { sharpe: 1.08, max_drawdown: 0.13, latency_ms: 138 },
      metadata: { strategy: "candidate" }
    },
    visualization: {
      workflow_id: "quant-demo",
      run_id: "candidate-run-002",
      nodes: [
        { id: "data", name: "Load data", type: "tool", metadata: { traced: true } },
        { id: "agent", name: "Strategy agent", type: "agent", metadata: { traced: true } },
        { id: "risk", name: "Risk check", type: "tool", metadata: { traced: true } }
      ],
      edges: [
        { source: "data", target: "agent", type: "sequence", metadata: {} },
        { source: "agent", target: "risk", type: "sequence", metadata: {} }
      ],
      run_path: ["data", "agent", "risk"],
      total_nodes: 3,
      traced_node_ids: ["data", "agent", "risk"],
      metric_node_ids: ["agent", "risk"],
      black_box_node_ids: ["risk"],
      error_node_ids: [],
      trace_coverage: 0.67,
      metric_coverage: 0.67,
      node_costs: { agent: 0.15, risk: 0.02 },
      node_latencies_ms: { data: 20, agent: 110, risk: 8 }
    },
    report: {
      workflow_id: "quant-demo",
      run_id: "candidate-run-002",
      baseline_run_id: null,
      candidate_run_id: null,
      run_kind: "historical",
      trace_coverage: 0.67,
      metric_coverage: 0.67,
      black_box_node_ids: ["risk"],
      business_metrics: { sharpe: 1.08, max_drawdown: 0.13 },
      system_metrics: { latency_ms: 138 },
      data_quality_metrics: { sample_count: 120 },
      comparison: null,
      recommendation: "candidate_ready",
      summary: "Candidate strategy improves return profile with acceptable latency.",
      evidence: {
        quality: {
          status: "warning",
          score: 0.55,
          reasons: ["low_trace_coverage", "black_box_nodes_present"]
        }
      }
    }
  },
  {
    run: {
      workflow_id: "tradingagents_quant_research",
      run_id: "ta-candidate-001",
      scenario_id: "quant",
      run_kind: "historical",
      metrics: { sharpe: 1.31, max_drawdown: 0.11, total_return: 0.26, sample_count: 504 },
      metadata: { source: "tradingagents_spike" }
    },
    visualization: {
      workflow_id: "tradingagents_quant_research",
      run_id: "ta-candidate-001",
      nodes: [
        { id: "market_analyst", name: "Market Analyst", type: "agent", metadata: { traced: true } },
        { id: "researcher", name: "Strategy Researcher", type: "agent", metadata: { traced: true } },
        { id: "risk_manager", name: "Risk Manager", type: "agent", metadata: { traced: true } },
        { id: "backtester", name: "Backtester", type: "tool", metadata: { traced: true } }
      ],
      edges: [
        { source: "market_analyst", target: "researcher", type: "sequence", metadata: {} },
        { source: "researcher", target: "risk_manager", type: "sequence", metadata: {} },
        { source: "risk_manager", target: "backtester", type: "sequence", metadata: {} }
      ],
      run_path: ["market_analyst", "researcher", "risk_manager", "backtester"],
      total_nodes: 4,
      traced_node_ids: ["market_analyst", "researcher", "risk_manager", "backtester"],
      metric_node_ids: ["risk_manager", "backtester"],
      black_box_node_ids: [],
      error_node_ids: [],
      trace_coverage: 1,
      metric_coverage: 0.5,
      node_costs: { market_analyst: 0.08, researcher: 0.12, risk_manager: 0.04, backtester: 0.02 },
      node_latencies_ms: { market_analyst: 1400, researcher: 2100, risk_manager: 900, backtester: 3200 }
    },
    report: {
      workflow_id: "tradingagents_quant_research",
      run_id: "ta-candidate-001",
      baseline_run_id: null,
      candidate_run_id: null,
      run_kind: "historical",
      trace_coverage: 1,
      metric_coverage: 0.5,
      black_box_node_ids: [],
      business_metrics: { sharpe: 1.31, max_drawdown: 0.11, total_return: 0.26 },
      system_metrics: {},
      data_quality_metrics: { sample_count: 504 },
      comparison: null,
      recommendation: "continue_shadow",
      summary: "TradingAgents-like candidate converted through export-only spike.",
      evidence: { quality: { status: "accepted", score: 1, reasons: [] } }
    }
  }
];

const comparisonReport = {
  workflow_id: "quant-demo",
  run_id: null,
  baseline_run_id: "baseline-run-001",
  candidate_run_id: "candidate-run-002",
  run_kind: "historical",
  trace_coverage: 0.67,
  metric_coverage: 0.67,
  black_box_node_ids: ["risk"],
  business_metrics: { sharpe: 1.08, max_drawdown: 0.13 },
  system_metrics: { latency_ms: 138 },
  data_quality_metrics: { sample_count: 120 },
  comparison: {
    metric_diffs: { sharpe: 0.26, max_drawdown: -0.05, latency_ms: 18, sample_count: 0 },
    business_metric_diffs: { sharpe: 0.26, max_drawdown: -0.05 },
    system_metric_diffs: { latency_ms: 18 },
    data_quality_metric_diffs: { sample_count: 0 },
    metric_evaluations: {},
    objective_score: 0.31,
    guardrail_violations: [],
    improved: true,
    summary: "Candidate improves Sharpe and lowers drawdown versus baseline.",
    run_kind: "historical",
    provenance: { source: "e2e-fixture" }
  },
  recommendation: "approve_candidate",
  summary: "Candidate improves Sharpe and lowers drawdown versus baseline.",
  evidence: {
    quality: {
      status: "warning",
      score: 0.55,
      reasons: ["low_trace_coverage", "black_box_nodes_present"]
    }
  }
};

function graphForRun(runId: string) {
  const stored = evidenceRuns.find((item) => item.run.run_id === runId) ?? evidenceRuns[1];
  const metricSources: Record<string, string[]> = {};
  for (const nodeId of stored.visualization.metric_node_ids) {
    if (nodeId === "agent") {
      metricSources.sharpe = ["agent"];
    }
    if (nodeId === "risk") {
      metricSources.max_drawdown = ["risk"];
    }
  }
  return {
    workflow_id: stored.run.workflow_id,
    run_id: stored.run.run_id,
    scenario_id: stored.run.scenario_id,
    nodes: stored.visualization.nodes.map((node, index) => ({
      id: node.id,
      label: node.name ?? node.id,
      node_type: node.type,
      status: "succeeded",
      layout: { x: index, y: 0 },
      metric_names: Object.entries(metricSources)
        .filter(([, sources]) => sources.includes(node.id))
        .map(([metric]) => metric),
      artifact_refs: [],
      black_box: stored.visualization.black_box_node_ids.includes(node.id),
      error: stored.visualization.error_node_ids.includes(node.id),
      high_cost: node.id === "agent",
      high_latency: node.id === "agent",
      optimizable: node.id === "agent",
      gaps:
        node.id === "risk"
          ? [
              {
                code: "node.black_box",
                severity: "warning",
                message: "Node risk is not fully observable.",
                node_id: "risk",
                details: {}
              }
            ]
          : [],
      metadata: node.metadata
    })),
    edges: stored.visualization.edges.map((edge) => ({
      source: edge.source,
      target: edge.target,
      edge_type: edge.type,
      active: true,
      metadata: edge.metadata
    })),
    run_path: stored.visualization.run_path,
    metric_sources: metricSources,
    filters: {
      black_box: stored.visualization.black_box_node_ids,
      error: stored.visualization.error_node_ids,
      metric: stored.visualization.metric_node_ids,
      high_cost: ["agent"],
      high_latency: ["agent"]
    },
    legend: {
      black_box: "Node has incomplete observability.",
      error: "Node has failed trace evidence.",
      metric: "Node produced at least one metric.",
      high_cost: "Node has the highest observed cost in this run.",
      high_latency: "Node has the highest observed latency in this run."
    },
    summary: `Graph for ${stored.run.workflow_id}/${stored.run.run_id}.`
  };
}

const optimizationChart = {
  workflow_id: "quant-demo",
  scenario_id: "quant",
  baseline_run_id: "baseline-run-001",
  baseline_metrics: { sharpe: 0.82, max_drawdown: 0.18 },
  candidate_points: [
    {
      run_id: "candidate-run-002",
      scenario_id: "quant",
      run_kind: "historical",
      total_return: 0.28,
      sharpe: 1.08,
      max_drawdown: 0.13,
      win_rate: 0.58,
      turnover: 1.6,
      objective_score: 0.31,
      guardrail_status: "ok",
      candidate_quality: "candidate",
      best_candidate: true,
      summary: "candidate-run-002 improved Sharpe without violating drawdown.",
      metadata: {}
    },
    {
      run_id: "weak-run-003",
      scenario_id: "quant",
      run_kind: "historical",
      total_return: 0.08,
      sharpe: 0.42,
      max_drawdown: 0.28,
      win_rate: 0.42,
      turnover: 4.2,
      objective_score: -0.4,
      guardrail_status: "violated",
      candidate_quality: "weak",
      best_candidate: false,
      summary: "weak-run-003 violated max_drawdown.",
      metadata: {}
    }
  ],
  metric_trends: [],
  chart_fields: ["total_return", "sharpe", "max_drawdown", "objective_score"],
  guardrail_summary: "1 candidates violated guardrails: weak-run-003.",
  best_candidate_run_id: "candidate-run-002",
  summary: "Baseline baseline-run-001 compared with 2 candidates; best=candidate-run-002; guardrail_violations=1."
};

const reviewPackage = {
  package_id: "review_quant_demo_baseline_run_001_1",
  workflow_id: "quant-demo",
  scenario_id: "quant",
  baseline_run_id: "baseline-run-001",
  candidate_run_ids: ["candidate-run-002"],
  graph: graphForRun("candidate-run-002"),
  chart: optimizationChart,
  comparison_reports: [comparisonReport],
  gap_summary: "1 evidence gaps across candidates.",
  recommended_action: "review_for_paper",
  markdown: [
    "# Evidence Review Package",
    "",
    "Package: review_quant_demo_baseline_run_001_1",
    "Baseline: baseline-run-001",
    "Candidates: candidate-run-002",
    "",
    "## Guardrail Summary",
    "1 candidates violated guardrails: weak-run-003.",
    "",
    "## Next Action",
    "review_for_paper"
  ].join("\n"),
  metadata: {
    best_candidate_run_id: "candidate-run-002",
    candidate_count: 1,
    comparison_count: 1
  }
};

const reviewDecision = {
  decision_id: "review-decision-001",
  package_id: reviewPackage.package_id,
  scenario_id: "quant",
  workflow_id: "quant-demo",
  baseline_run_id: "baseline-run-001",
  candidate_run_ids: ["candidate-run-002"],
  recommended_action: "review_for_paper",
  status: "pending",
  reason: "Candidate package created from baseline/candidate evidence for human review.",
  approval_required: true,
  comment: null,
  created_at: "2026-06-11T00:00:00Z",
  decided_at: null,
  metadata: {
    package_markdown: reviewPackage.markdown,
    guardrail_summary: reviewPackage.chart.guardrail_summary
  }
};

let activeBaselineRunId = "";

test("renders the control console shell", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("Loop Harness").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByLabel("API Token")).toBeVisible();
  await expect(page.getByRole("link", { name: "Approvals" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Evidence" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Workflows" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Runs" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Shadows" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Charts" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Learning" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Autonomy" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Reports" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Config", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Agent Config" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Profile" })).toBeVisible();
});

test("opens the evidence console page", async ({ page }) => {
  activeBaselineRunId = "";
  await page.route("**/api/evidence/runs", async (route) => {
    await route.fulfill({ json: evidenceRuns });
  });
  await page.route("**/api/evidence/runs/*/gaps", async (route) => {
    await route.fulfill({
      json: {
        workflow_id: "quant-demo",
        run_id: "candidate-run-002",
        status: "warning",
        gaps: [
          {
            code: "node.black_box",
            severity: "warning",
            message: "Node risk is not fully observable.",
            node_id: "risk",
            details: {}
          }
        ],
        black_box_node_ids: ["risk"],
        missing_metric_node_ids: ["data"],
        missing_trace_node_ids: [],
        summary: "Run candidate-run-002 has 1 evidence gaps; status=warning."
      }
    });
  });
  await page.route("**/api/evidence/runs/*/graph", async (route) => {
    const runId = route.request().url().split("/").at(-2) ?? "";
    await route.fulfill({ json: graphForRun(runId) });
  });
  await page.route("**/api/evidence/workflows/*/graph", async (route) => {
    await route.fulfill({ json: graphForRun("candidate-run-002") });
  });
  await page.route("**/api/evidence/workflows/*/charts/optimization", async (route) => {
    await route.fulfill({ json: optimizationChart });
  });
  await page.route("**/api/evidence/review-packages/validate", async (route) => {
    await route.fulfill({
      json: {
        package_id: reviewPackage.package_id,
        valid: true,
        missing_run_ids: [],
        drifted_run_ids: [],
        summary: "Review package is replay-valid."
      }
    });
  });
  await page.route("**/api/evidence/review-packages", async (route) => {
    await route.fulfill({ json: reviewPackage });
  });
  await page.route("**/api/evidence/review-packages/submit", async (route) => {
    await route.fulfill({ json: reviewDecision });
  });
  await page.route("**/api/approvals", async (route) => {
    await route.fulfill({
      json: [
        {
          id: reviewDecision.decision_id,
          scenario_id: "quant",
          item_type: "evidence_review_package",
          source_id: reviewDecision.decision_id,
          title: `Evidence review package: ${reviewDecision.package_id}`,
          summary: reviewDecision.reason,
          status: "pending",
          recommended_action: "review_for_paper",
          created_at: reviewDecision.created_at
        }
      ]
    });
  });
  await page.route("**/api/approvals/**", async (route) => {
    const url = route.request().url();
    if (route.request().method() === "POST" && url.endsWith("/approve")) {
      await route.fulfill({ json: { id: reviewDecision.decision_id, updated: true } });
      return;
    }
    await route.fulfill({
      json: {
        id: reviewDecision.decision_id,
        scenario_id: "quant",
        item_type: "evidence_review_package",
        source_id: reviewDecision.decision_id,
        title: `Evidence review package: ${reviewDecision.package_id}`,
        summary: reviewDecision.reason,
        status: "pending",
        recommended_action: "review_for_paper",
        created_at: reviewDecision.created_at,
        detail: reviewDecision
      }
    });
  });
  await page.route("**/api/evidence/runs/*/nodes/*", async (route) => {
    const url = route.request().url();
    const nodeId = url.split("/").pop() ?? "";
    await route.fulfill({
      json: {
        workflow_id: "quant-demo",
        run_id: "candidate-run-002",
        node_id: nodeId,
        name: nodeId === "agent" ? "Strategy agent" : "Risk check",
        type: nodeId === "agent" ? "agent" : "tool",
        status: "succeeded",
        input_summary: "bars + config",
        output_summary: nodeId === "agent" ? "candidate signal" : "risk passed",
        metrics: nodeId === "agent" ? { sharpe: 1.08 } : { max_drawdown: 0.13 },
        latency_ms: nodeId === "agent" ? 110 : 8,
        cost: nodeId === "agent" ? 0.15 : 0.02,
        error: null,
        black_box: nodeId === "risk",
        optimizable: nodeId === "agent",
        artifact_refs:
          nodeId === "agent"
            ? [{ type: "json", path: "runs/candidate-signal.json", metadata: { node_id: "agent" } }]
            : [{ type: "log", path: "runs/risk-check.log", metadata: { node_id: "risk" } }],
        gaps:
          nodeId === "risk"
            ? [
                {
                  code: "node.black_box",
                  severity: "warning",
                  message: "Node risk is not fully observable.",
                  node_id: "risk",
                  details: {}
                }
              ]
            : [],
        metadata: {}
      }
    });
  });
  await page.route("**/api/evidence/goals/quant", async (route) => {
    await route.fulfill({
      json: {
        scenario_id: "quant",
        primary_metrics: ["sharpe"],
        guardrail_metrics: ["max_drawdown"],
        max_cost_increase: 0.1,
        max_risk_level: "approval",
        preferences: { trading_frequency: "low" }
      }
    });
  });
  await page.route("**/api/evidence/decision-memory/quant", async (route) => {
    await route.fulfill({
      json: {
        scenario_id: "quant",
        approved_count: 1,
        rejected_count: 0,
        approved_patterns: ["prompt", "sharpe"],
        rejected_patterns: [],
        summary: "Scenario quant: 1 approvals, 0 rejections. Use this as decision context, not automatic authority."
      }
    });
  });
  await page.route("**/api/user-profile**", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        json: {
          id: "suggested-notes-001",
          actor: "hermes",
          content: "# Suggested Profile Notes\n\nHermes draft: user may prefer lower drawdown.\n\nStatus: pending human review",
          created_at: "2026-06-12T00:00:00Z",
          metadata: {}
        }
      });
      return;
    }
    await route.fulfill({
      json: {
        formal_profile: "# User Profile\n\nDo not execute live trading without explicit human approval.",
        suggested_notes: "# Suggested Profile Notes\n\nHermes draft: user may prefer lower drawdown.",
        versions: []
      }
    });
  });
  await page.route("**/api/evidence/runs/*", async (route) => {
    if (
      route.request().url().includes("/gaps") ||
      route.request().url().includes("/graph") ||
      route.request().url().includes("/nodes/")
    ) {
      await route.fallback();
      return;
    }
    const runId = route.request().url().split("/").pop() ?? "";
    const stored = evidenceRuns.find((item) => item.run.run_id === runId);
    if (!stored) {
      await route.fulfill({ status: 404, json: { code: "evidence.run_not_found", message: "Missing", details: {} } });
      return;
    }
    await route.fulfill({ json: stored });
  });
  await page.route("**/api/evidence/compare", async (route) => {
    await route.fulfill({ json: comparisonReport });
  });
  await page.route("**/api/evidence/proposals", async (route) => {
    await route.fulfill({
      json: {
        id: "evidence-proposal-001",
        scenario_id: "quant",
        proposal_kind: "evidence",
        target_type: "deployment",
        target_id: "quant-demo:candidate-run-002",
        patch: {
          operation: "replace",
          before: { baseline_run_id: "baseline-run-001" },
          after: { candidate_run_id: "candidate-run-002" }
        },
        reason: "Candidate improves Sharpe and lowers drawdown versus baseline.",
        expected_metric: "objective_score",
        status: "proposed",
        created_at: "2026-06-11T00:00:00Z",
        updated_at: "2026-06-11T00:00:00Z",
        metadata: {}
      }
    });
  });
  await page.route("**/api/evidence/workflows/*/baseline", async (route) => {
    if (route.request().method() === "POST") {
      const body = route.request().postDataJSON() as { baseline_run_id: string; reason: string };
      activeBaselineRunId = body.baseline_run_id;
      await route.fulfill({
        json: {
          workflow_id: "quant-demo",
          baseline_run_id: activeBaselineRunId,
          reason: body.reason,
          created_at: "2026-06-11T00:00:00Z"
        }
      });
      return;
    }
    if (!activeBaselineRunId) {
      await route.fulfill({
        status: 404,
        json: { code: "evidence.baseline_not_found", message: "Missing", details: {} }
      });
      return;
    }
    await route.fulfill({
      json: {
        workflow_id: "quant-demo",
        baseline_run_id: activeBaselineRunId,
        reason: "Pinned from UI.",
        created_at: "2026-06-11T00:00:00Z"
      }
    });
  });

  await page.goto("/");

  await page.getByRole("link", { name: "Evidence", exact: true }).click();

  await expect(page).toHaveURL(/\/evidence$/);
  await expect(page.getByRole("heading", { name: "Evidence Runs" })).toBeVisible();
  await expect(page.getByText("Workflow Visualization")).toBeVisible();
  await expect(page.getByRole("button", { name: "baseline…" })).toBeVisible();
  await expect(page.getByRole("button", { name: "candidat…" })).toBeVisible();

  await page.getByRole("link", { name: "Open baseline…" }).click();

  await expect(page).toHaveURL(/\/evidence\/runs\/baseline-run-001$/);
  await expect(page.getByRole("heading", { name: "Evidence Run Detail" })).toBeVisible();
  await expect(page.getByText("Baseline strategy has enough trace coverage for comparison.")).toBeVisible();
  await expect(page.getByText("data → agent")).toBeVisible();

  await page.getByRole("button", { name: "Set as baseline" }).click();
  await expect(page.getByRole("button", { name: "Active baseline" })).toBeVisible();

  await page.getByRole("link", { name: "Back to evidence" }).click();
  await expect(page.getByText("Active baseline").first()).toBeVisible();

  await page.getByRole("link", { name: "Open candidat…" }).click();
  await expect(page).toHaveURL(/\/evidence\/runs\/candidate-run-002$/);
  await page.getByRole("button", { name: "Create review package" }).click();
  await expect(page.getByText("review_quant_demo_baseline_run_001_1").first()).toBeVisible();
  await expect(page.getByText("review_for_paper").first()).toBeVisible();
  await expect(page.getByText("Evidence Review Package")).toBeVisible();
  await page.getByRole("button", { name: "Submit for approval" }).click();
  await expect(page.getByText("Decision review-decision-001 is pending.")).toBeVisible();
  await page.getByRole("link", { name: "Approvals" }).click();
  await expect(page.getByRole("heading", { name: "Approval Inbox" })).toBeVisible();
  await page.getByRole("link", { name: "Evidence review package: review_quant_demo_baseline_run_001_1" }).click();
  await expect(page.getByRole("heading", { name: "Approval Detail" })).toBeVisible();
  await expect(page.getByText("baseline-run-001").first()).toBeVisible();
  await expect(page.getByText("candidate-run-002").first()).toBeVisible();
  await page.getByPlaceholder("Decision note").fill("Approved for paper review.");
  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page).toHaveURL(/\/approvals$/);
  await page.getByRole("link", { name: "Evidence", exact: true }).click();
  await expect(page).toHaveURL(/\/evidence$/);

  await page.getByRole("button", { name: "candidat…" }).click();

  await page.getByRole("button", { name: "candidat…" }).click();

  await expect(page.getByText("Load data")).toBeVisible();
  await expect(page.getByText("Strategy agent")).toBeVisible();
  await expect(page.getByText("data → agent → risk")).toBeVisible();
  await expect(page.getByText("Graph evidence")).toBeVisible();
  await expect(page.getByText("Metric sources")).toBeVisible();
  await expect(page.getByText("Optimization Charts")).toBeVisible();
  await expect(page.getByText("Optimization impact chart")).toBeVisible();
  await expect(page.getByText("Baseline vs best candidate")).toBeVisible();
  await expect(page.getByText("Sharpe uplift")).toBeVisible();
  await expect(page.getByText("Drawdown change")).toBeVisible();
  await expect(page.getByText("candidate-run-002").first()).toBeVisible();
  await expect(page.getByText("weak-run-003").first()).toBeVisible();
  await expect(page.getByText("1 candidates violated guardrails: weak-run-003.").first()).toBeVisible();
  await expect(page.getByText("Traced").first()).toBeVisible();
  await expect(page.getByText("Metric").first()).toBeVisible();
  await expect(page.getByText("Black box").first()).toBeVisible();
  await expect(page.getByText("Error").first()).toBeVisible();
  await expect(page.getByText("Evidence Quality")).toBeVisible();
  await expect(page.getByText("warning").first()).toBeVisible();
  await expect(page.getByText("black_box_nodes_present")).toBeVisible();
  await expect(page.getByText("Baseline vs Candidate")).toBeVisible();
  await expect(page.getByLabel("Baseline run")).toBeVisible();
  await expect(page.getByLabel("Candidate run")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Metric Delta" })).toBeVisible();

  await page.getByRole("button", { name: "Strategy agent" }).click();

  const nodeEvidence = page.locator("section").filter({ has: page.getByRole("heading", { name: "Node Evidence" }) });
  await expect(nodeEvidence.getByRole("heading", { name: "Node Evidence" })).toBeVisible();
  await expect(nodeEvidence.getByText("Node id")).toBeVisible();
  await expect(nodeEvidence.getByText("agent", { exact: true }).first()).toBeVisible();
  await expect(nodeEvidence.getByText("Type", { exact: true }).first()).toBeVisible();
  await expect(nodeEvidence.getByText("110 ms")).toBeVisible();
  await expect(nodeEvidence.getByText("$0.150")).toBeVisible();
  await expect(nodeEvidence.getByText("Metric captured")).toBeVisible();
  await expect(nodeEvidence.getByText("Optimizable")).toBeVisible();
  await expect(nodeEvidence.getByText("candidate signal")).toBeVisible();
  await expect(nodeEvidence.getByText("Artifacts")).toBeVisible();
  await expect(nodeEvidence.getByText("runs/candidate-signal.json")).toBeVisible();

  await page.getByRole("button", { name: "Risk check" }).click();
  await expect(nodeEvidence.getByText("Black-box node")).toBeVisible();
  await expect(nodeEvidence.getByText("Evidence gaps")).toBeVisible();
  await expect(nodeEvidence.getByText("node.black_box").first()).toBeVisible();
  await expect(nodeEvidence.getByText("runs/risk-check.log")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Evidence Gaps" })).toBeVisible();
  await expect(page.getByText("Node risk is not fully observable.").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Optimization Goal" })).toBeVisible();
  await expect(page.getByText("Primary: sharpe")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Decision Memory" })).toBeVisible();
  await expect(page.getByText("Scenario quant: 1 approvals, 0 rejections.")).toBeVisible();
  await expect(page.getByText("Approved patterns")).toBeVisible();
  await expect(page.getByText("prompt, sharpe")).toBeVisible();

  await page.getByRole("button", { name: "Compare" }).click();

  await expect(page.getByText("approve_candidate")).toBeVisible();
  await expect(page.getByText("Candidate improves Sharpe and lowers drawdown versus baseline.")).toBeVisible();
  await expect(page.getByText("sharpe", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("business / +0.260")).toBeVisible();
  await expect(page.getByText("max_drawdown", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("system / +18.000")).toBeVisible();
  await expect(page.getByText("Impact Summary")).toBeVisible();
  await expect(page.getByText("Business metrics improved: 1; worsened: 1; system metrics tracked: 1.")).toBeVisible();
  await page.getByRole("button", { name: "Create approval proposal" }).click();
  await expect(page.getByRole("link", { name: "Open approval evidence-proposal-001" })).toBeVisible();
  await expect(page.getByText("What to do next")).toBeVisible();
  await expect(page.getByText("Review candidate approval")).toBeVisible();
  await expect(page.getByText("Add trace coverage before trusting this workflow")).toBeVisible();
  await expect(page.getByText("Improve metric capture before optimization")).toBeVisible();

  await page.getByRole("link", { name: "Workflows" }).click();
  await expect(page).toHaveURL(/\/workflows$/);
  await expect(page.getByRole("heading", { name: "Workflow Maps" })).toBeVisible();
  await expect(page.getByText("Imported workflow structures")).toBeVisible();
  await expect(page.getByRole("heading", { name: "quant-demo" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "tradingagents_quant_research" })).toBeVisible();
  await expect(page.getByText("Market Analyst -> Strategy Researcher -> Risk Manager -> Backtester")).toBeVisible();

  await page.getByRole("link", { name: "Charts" }).click();
  await expect(page).toHaveURL(/\/charts$/);
  await expect(page.getByRole("heading", { name: "Optimization Charts" })).toBeVisible();
  await expect(page.getByText("Baseline baseline-run-001 compared with 2 candidates").first()).toBeVisible();
  await expect(page.getByText("Baseline vs best candidate")).toBeVisible();
  await expect(page.getByText("weak-run-003").first()).toBeVisible();

  await page.goto("/profile");
  await expect(page).toHaveURL(/\/profile$/);
  await expect(page.getByRole("heading", { name: "User Profile" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Formal Profile" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Suggested Notes" })).toBeVisible();
  await expect(page.getByText("Do not execute live trading without explicit human approval.")).toBeVisible();
  await expect(page.getByText("Hermes draft: user may prefer lower drawdown.")).toBeVisible();
  await page.getByRole("button", { name: "Ask Hermes to summarize" }).click();
  await expect(page.getByText("Hermes draft updated. Review it before changing the formal profile.")).toBeVisible();
});
