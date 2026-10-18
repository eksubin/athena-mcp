import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { apiFetch } from "@/lib/api";
import type {
  AdminAccount,
  AdminInvite,
  AdminOverview,
  Profile,
} from "@/lib/types";
import { Icon, PageHeading, SectionHeading } from "@/components/ui";
import AdminConsole from "./admin-console";

export default async function AdminPage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) redirect("/login");

  // The API refuses these three to a member (403); checking the role first
  // turns that into a redirect rather than a crashed render for anyone who
  // simply typed the URL.
  const profile = await apiFetch<Profile>("/profile", session.access_token);
  if (profile.role !== "admin") redirect("/dashboard");

  const [overview, accounts, invites] = await Promise.all([
    apiFetch<AdminOverview>("/admin/overview", session.access_token),
    apiFetch<AdminAccount[]>("/admin/users", session.access_token),
    apiFetch<AdminInvite[]>("/admin/invites", session.access_token),
  ]);

  return (
    <>
      <PageHeading
        eyebrow="Administration"
        title="Who’s inside, and who’s invited."
        description="Athena is invite-only. Manage accounts, invite allowances, and the addresses allowed to join."
      />
      <div className="overview-grid" aria-label="Access summary">
        <section className="card metric-card metric-wide">
          <div className="metric-top">
            <span>Accounts</span>
            <Icon name="users" size={18} />
          </div>
          <div className="metric-bottom">
            <p className="metric-number">
              {(overview.members + overview.admins)
                .toString()
                .padStart(2, "0")}
            </p>
            <span className="metric-caption">
              {overview.admins} administrator
              {overview.admins === 1 ? "" : "s"}
              <br />
              {overview.disabled} without access
            </span>
          </div>
          <p className="metric-note">Everyone who has joined so far</p>
        </section>
        <section className="card metric-card">
          <div className="metric-top">
            <span>Waiting to join</span>
            <Icon name="mail" size={18} />
          </div>
          <p className="metric-number">
            {overview.pending_invites.toString().padStart(2, "0")}
          </p>
          <p className="metric-note">Invited, not yet signed in</p>
        </section>
        <section className="card metric-card">
          <div className="metric-top">
            <span>Access withdrawn</span>
            <Icon name="ban" size={18} />
          </div>
          <p className="metric-number">
            {overview.disabled.toString().padStart(2, "0")}
          </p>
          <p className="metric-note">Suspended accounts keep their data</p>
        </section>
      </div>
      <section className="card card-pad" style={{ marginTop: 28 }}>
        <SectionHeading
          icon="shield"
          title="Accounts and invites"
          description="Change someone’s role or invite allowance, withdraw access, or add an address to the allowlist."
        />
        <AdminConsole
          initialAccounts={accounts}
          initialInvites={invites}
          currentUserId={profile.id}
        />
      </section>
    </>
  );
}
