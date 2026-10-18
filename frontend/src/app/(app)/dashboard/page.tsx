import { redirect } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { apiFetch } from "@/lib/api";
import type { Application } from "@/lib/types";
import { Icon, PageHeading } from "@/components/ui";
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
        action={
          <Link href="/profile" className="button button-primary">
            <Icon name="user" size={16} /> My profile{" "}
            <Icon name="arrow" size={15} />
          </Link>
        }
      />
      <StatusBoard initialApplications={applications} />
      <div className="dashboard-bottom">
        <section className="card action-card">
          <span className="icon-tile">
            <Icon name="file" />
          </span>
          <div>
            <h3>Put your best story forward.</h3>
            <p>
              Keep your resume, preferences, and reusable answers ready for the
              right opportunity.
            </p>
            <Link href="/profile" className="text-action">
              Shape your profile <Icon name="arrow" size={14} />
            </Link>
          </div>
        </section>
        <section className="card action-card">
          <span className="icon-tile">
            <Icon name="world" />
          </span>
          <div>
            <h3>Progress you can see.</h3>
            <p>
              Saved roles plant saplings. Interviews build houses. Watch your
              world grow with you.
            </p>
            <Link href="/world" className="text-action">
              Explore your world <Icon name="arrow" size={14} />
            </Link>
          </div>
        </section>
      </div>
    </>
  );
}
