"use client";

import { useState, useTransition } from "react";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import type { Application, ApplicationStatus, JobSummary } from "@/lib/types";

const STATUSES: ApplicationStatus[] = [
  "saved",
  "applied",
  "pending",
  "interview",
  "offer",
  "rejected",
];

const STATUS_LABELS: Record<ApplicationStatus, string> = {
  saved: "Saved",
  applied: "Applied",
  pending: "Pending",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
};

// What "move forward" means from each status — rejection happens from the
// job's side, not a button a user clicks on themselves, so it's absent here.
const NEXT_STATUS: Partial<Record<ApplicationStatus, ApplicationStatus>> = {
  saved: "applied",
  applied: "pending",
  pending: "interview",
  interview: "offer",
};

interface Props {
  initialApplications: Application[];
  jobById: Record<string, JobSummary>;
}

export default function StatusBoard({ initialApplications, jobById }: Props) {
  const [applications, setApplications] = useState(initialApplications);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [, startTransition] = useTransition();

  async function advance(app: Application) {
    const next = NEXT_STATUS[app.status];
    if (!next) return;

    setBusyId(app.id);
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) return;

      const updated = await apiFetch<Application>(`/applications/${app.id}`, session.access_token, {
        method: "PATCH",
        body: JSON.stringify({ status: next }),
      });
      startTransition(() => {
        setApplications((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
      });
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
      {STATUSES.map((status) => {
        const inColumn = applications.filter((a) => a.status === status);
        return (
          <div key={status} className="rounded-lg border border-stone-200 bg-stone-100/60 p-3">
            <h2 className="mb-3 text-xs font-semibold tracking-wide text-stone-500 uppercase">
              {STATUS_LABELS[status]}{" "}
              <span className="font-normal text-stone-400">({inColumn.length})</span>
            </h2>
            <div className="flex flex-col gap-2">
              {inColumn.map((a) => {
                const job = jobById[a.job_id];
                const next = NEXT_STATUS[a.status];
                return (
                  <div
                    key={a.id}
                    className="rounded-md border border-stone-200 bg-white p-3 shadow-sm"
                  >
                    <p className="text-sm font-medium text-stone-900">
                      {job?.title ?? "Unknown role"}
                    </p>
                    <p className="text-xs text-stone-500">{job?.company}</p>
                    {next && (
                      <button
                        onClick={() => advance(a)}
                        disabled={busyId === a.id}
                        className="mt-2 text-xs font-medium text-emerald-700 hover:underline disabled:opacity-50"
                      >
                        {busyId === a.id ? "Moving…" : `Move to ${STATUS_LABELS[next]} →`}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
