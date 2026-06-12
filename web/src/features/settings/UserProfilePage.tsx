import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getUserProfile, suggestUserProfile } from "../../api/client";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { PageHeader } from "../../components/PageHeader";

export function UserProfilePage() {
  const queryClient = useQueryClient();
  const profile = useQuery({ queryKey: ["user-profile"], queryFn: getUserProfile });
  const suggest = useMutation({
    mutationFn: () => suggestUserProfile(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["user-profile"] });
    }
  });

  return (
    <>
      <PageHeader title="User Profile" description="Formal human-owned preferences and separate Hermes draft notes." />
      {profile.data ? (
        <div className="space-y-4">
          <div className="rounded-md border border-border bg-panel p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="text-sm font-medium text-ink">Hermes draft helper</div>
                <p className="mt-1 text-sm text-muted">
                  Generates draft notes from decision history. It never edits the formal profile.
                </p>
              </div>
              <button
                className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                disabled={suggest.isPending}
                onClick={() => suggest.mutate()}
              >
                {suggest.isPending ? "Summarizing..." : "Ask Hermes to summarize"}
              </button>
            </div>
            {suggest.isSuccess ? (
              <p className="mt-3 text-sm text-emerald-700">
                Hermes draft updated. Review it before changing the formal profile.
              </p>
            ) : null}
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
          <Card title="Formal Profile">
            <pre className="whitespace-pre-wrap text-sm text-ink">{profile.data.formal_profile}</pre>
          </Card>
          <Card title="Suggested Notes">
            <pre className="whitespace-pre-wrap text-sm text-muted">
              {suggest.data?.content ?? profile.data.suggested_notes}
            </pre>
          </Card>
          </div>
        </div>
      ) : (
        <EmptyState title="No profile loaded" body="Enter an API token to load the formal user profile." />
      )}
    </>
  );
}
