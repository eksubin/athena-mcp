import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { apiFetch } from "@/lib/api";
import type { Profile } from "@/lib/types";
import Nav from "@/components/nav";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) redirect("/login");

  // Also doubles as the lazy profile/plot creation trigger for a
  // brand-new user's first visit — the backend creates both on first
  // authenticated request.
  //
  // It is also where withdrawn access surfaces: Athena is invite-only, and
  // an account whose access an administrator took away still holds a valid
  // session until it expires, so the API refuses it with a 403 rather than
  // the session simply being gone. Showing the workspace shell around that
  // error would be worse than sending them back to the door.
  let profile: Profile;
  try {
    profile = await apiFetch<Profile>("/profile", session.access_token);
  } catch (caught) {
    if (caught instanceof Error && caught.message.includes("(403)"))
      redirect("/login?error=access");
    throw caught;
  }

  return (
    <div className="app-shell">
      <Nav
        username={profile.username}
        avatar={profile.avatar}
        isAdmin={profile.role === "admin"}
      />
      <div className="workspace">
        <header className="workspace-topbar">
          <div className="breadcrumb">
            <span>Workspace</span>
            <span>/</span>
            <strong>Your career, thoughtfully organized</strong>
          </div>
          <span className="workspace-label">Personal space</span>
        </header>
        <main className="main-content" id="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}
