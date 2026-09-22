import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { apiFetch } from "@/lib/api";
import type { Application, JobSummary } from "@/lib/types";
import StatusBoard from "./status-board";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) redirect("/login");

  const applications = await apiFetch<Application[]>("/applications", session.access_token);
  const jobs = await Promise.all(
    applications.map((a) => apiFetch<JobSummary>(`/jobs/${a.job_id}`, session.access_token)),
  );
  const jobById = Object.fromEntries(jobs.map((j) => [j.id, j]));

  return (
    <div>
      <h1 className="text-xl font-semibold text-stone-900">Applications</h1>
      <p className="mt-1 text-sm text-stone-500">
        {applications.length === 0
          ? "Nothing tracked yet — jobs saved or applied to via the MCP tools will show up here."
          : `${applications.length} tracked.`}
      </p>
      <div className="mt-6">
        <StatusBoard initialApplications={applications} jobById={jobById} />
      </div>
    </div>
  );
}
