import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { approveItem, getApiErrorMessage, getApproval, rejectItem } from "../../api/client";
import { Card } from "../../components/Card";
import { JsonBlock } from "../../components/JsonBlock";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { formatDate } from "../../lib/format";

export function ApprovalDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");
  const approval = useQuery({
    queryKey: ["approval", id],
    queryFn: () => getApproval(id),
    enabled: Boolean(id)
  });
  const approve = useMutation({
    mutationFn: () => approveItem(id, comment),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["approvals"] });
      navigate("/approvals");
    }
  });
  const reject = useMutation({
    mutationFn: () => rejectItem(id, comment),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["approvals"] });
      navigate("/approvals");
    }
  });

  const item = approval.data;
  const patch = item?.detail?.patch as
    | { slot?: string; operation?: string; before?: unknown; after?: unknown }
    | undefined;
  const reviewDecision =
    item?.item_type === "evidence_review_package" ? (item.detail as Record<string, unknown> | undefined) : undefined;
  const commentRequired = comment.trim().length === 0;

  return (
    <>
      <PageHeader
        title="Approval Detail"
        description="Review the reason, expected metric, and source payload before deciding."
      />
      <div className="grid gap-5 xl:grid-cols-[1fr_420px]">
        <Card title={item?.title ?? "Loading"}>
          {item ? (
            <div className="space-y-4 text-sm">
              <div className="flex flex-wrap gap-2">
                <StatusBadge value={item.status} />
                <span className="rounded border border-border px-2 py-0.5 text-xs text-muted">
                  {item.item_type}
                </span>
                <span className="rounded border border-border px-2 py-0.5 text-xs text-muted">
                  {item.scenario_id}
                </span>
              </div>
              <div>
                <div className="text-xs font-medium uppercase text-muted">Summary</div>
                <p className="mt-1 text-ink">{item.summary}</p>
              </div>
              <div>
                <div className="text-xs font-medium uppercase text-muted">Recommended Action</div>
                <p className="mt-1 text-ink">{item.recommended_action}</p>
              </div>
              <div>
                <div className="text-xs font-medium uppercase text-muted">Created</div>
                <p className="mt-1 text-ink">{formatDate(item.created_at)}</p>
              </div>
              {reviewDecision ? (
                <div className="grid gap-3 lg:grid-cols-3">
                  <div className="rounded-md border border-border bg-panel p-3">
                    <div className="text-xs font-medium uppercase text-muted">Baseline</div>
                    <p className="mt-1 break-all text-ink">{String(reviewDecision.baseline_run_id ?? "")}</p>
                  </div>
                  <div className="rounded-md border border-border bg-panel p-3">
                    <div className="text-xs font-medium uppercase text-muted">Candidates</div>
                    <p className="mt-1 break-all text-ink">
                      {Array.isArray(reviewDecision.candidate_run_ids)
                        ? reviewDecision.candidate_run_ids.join(", ")
                        : ""}
                    </p>
                  </div>
                  <div className="rounded-md border border-border bg-panel p-3">
                    <div className="text-xs font-medium uppercase text-muted">Package</div>
                    <p className="mt-1 break-all text-ink">{String(reviewDecision.package_id ?? "")}</p>
                  </div>
                </div>
              ) : null}
              {patch ? (
                <div className="grid gap-3 lg:grid-cols-2">
                  <div className="rounded-md border border-border bg-slate-50 p-3">
                    <div className="mb-2 text-xs font-medium uppercase text-muted">
                      Before {patch.slot ? `(${patch.slot})` : ""}
                    </div>
                    <pre className="whitespace-pre-wrap text-xs text-ink">{String(patch.before ?? "")}</pre>
                  </div>
                  <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3">
                    <div className="mb-2 text-xs font-medium uppercase text-emerald-700">
                      After {patch.operation ? `(${patch.operation})` : ""}
                    </div>
                    <pre className="whitespace-pre-wrap text-xs text-ink">{String(patch.after ?? "")}</pre>
                  </div>
                </div>
              ) : null}
              <JsonBlock value={item.detail ?? item} />
            </div>
          ) : (
            <p className="text-sm text-muted">Loading approval item.</p>
          )}
        </Card>
        <Card title="Decision">
          <label className="block text-sm text-muted">
            Comment
            <textarea
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              className="mt-2 min-h-32 w-full rounded-md border border-border px-3 py-2 text-sm text-ink outline-none focus:border-accent"
              placeholder="Decision note"
            />
          </label>
          <div className="mt-4 flex gap-3">
            <button
              className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              disabled={!item || commentRequired || approve.isPending || reject.isPending}
              onClick={() => approve.mutate()}
            >
              Approve
            </button>
            <button
              className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              disabled={!item || commentRequired || approve.isPending || reject.isPending}
              onClick={() => reject.mutate()}
            >
              Reject
            </button>
          </div>
          {commentRequired ? (
            <p className="mt-3 text-xs text-muted">A decision comment is required before action.</p>
          ) : null}
          {approve.error || reject.error ? (
            <p className="mt-3 text-sm text-red-700">{getApiErrorMessage(approve.error ?? reject.error)}</p>
          ) : null}
        </Card>
      </div>
    </>
  );
}
