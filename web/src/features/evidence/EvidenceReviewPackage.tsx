import type { EvidenceReviewPackage as EvidenceReviewPackagePayload } from "../../types/api";
import type { ReviewPackageDecision } from "../../types/api";

type EvidenceReviewPackageProps = {
  packageData?: EvidenceReviewPackagePayload;
  decision?: ReviewPackageDecision;
  disabled?: boolean;
  disabledReason?: string;
  isLoading?: boolean;
  isSubmitting?: boolean;
  onCreate: () => void;
  onSubmit?: () => void;
};

export function EvidenceReviewPackage({
  packageData,
  decision,
  disabled = false,
  disabledReason,
  isLoading = false,
  isSubmitting = false,
  onCreate,
  onSubmit
}: EvidenceReviewPackageProps) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-ink">Package the graph, chart, baseline comparison, and gaps for review.</p>
          {disabled && disabledReason ? <p className="mt-1 text-xs text-muted">{disabledReason}</p> : null}
        </div>
        <button
          className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-border disabled:text-muted"
          disabled={disabled || isLoading}
          onClick={onCreate}
        >
          {isLoading ? "Creating..." : "Create review package"}
        </button>
      </div>

      {packageData ? (
        <div className="space-y-3">
          <div className="grid gap-3 text-sm md:grid-cols-3">
            <div className="rounded border border-border p-3">
              <div className="text-xs uppercase text-muted">Package</div>
              <div className="mt-1 break-all font-medium text-ink">{packageData.package_id}</div>
            </div>
            <div className="rounded border border-border p-3">
              <div className="text-xs uppercase text-muted">Recommended action</div>
              <div className="mt-1 font-medium text-ink">{packageData.recommended_action}</div>
            </div>
            <div className="rounded border border-border p-3">
              <div className="text-xs uppercase text-muted">Candidates</div>
              <div className="mt-1 font-medium text-ink">{packageData.candidate_run_ids.length}</div>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 rounded border border-border bg-panel p-3">
            <div>
              <div className="text-sm font-medium text-ink">Approval decision</div>
              <p className="mt-1 text-xs text-muted">
                {decision
                  ? `Decision ${decision.decision_id} is ${decision.status}.`
                  : "Submit this evidence package to the human approval inbox."}
              </p>
            </div>
            <button
              className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-border disabled:text-muted"
              disabled={!onSubmit || Boolean(decision) || isSubmitting}
              onClick={onSubmit}
            >
              {decision ? "Submitted" : isSubmitting ? "Submitting..." : "Submit for approval"}
            </button>
          </div>

          <div className="rounded border border-border bg-surface p-3 text-sm">
            <div className="font-medium text-ink">Guardrail Summary</div>
            <p className="mt-1 text-muted">{packageData.chart.guardrail_summary}</p>
          </div>

          <pre className="max-h-80 overflow-auto rounded border border-border bg-ink p-3 text-xs text-white">
            {packageData.markdown}
          </pre>
        </div>
      ) : (
        <p className="text-sm text-muted">
          No review package has been created in this browser session. Create one after selecting a candidate against an
          active baseline.
        </p>
      )}
    </div>
  );
}
