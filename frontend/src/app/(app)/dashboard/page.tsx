import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { apiFetch } from "@/lib/api";
import type { Application } from "@/lib/types";
import { PageHeading } from "@/components/ui";
import StatusBoard from "./status-board";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) redirect("/login");
  // Each application arrives with its listing embedded, so this is one
  // request however long the pipeline gets — it used to be one more per
  // tracked job just to read a title.
  const applications = await apiFetch<Application[]>(
    "/applications",
    session.access_token,
  );
  return (
    <>
      <PageHeading
        eyebrow="A little more clarity. A lot more possibility."
        title="Your search, in focus."
        description="A home for every opportunity. Keep track of the next step, and how far you’ve come."
      />
      <StatusBoard initialApplications={applications} />
    </>
  );
}
