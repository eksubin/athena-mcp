import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { apiFetch } from "@/lib/api";
import type { Profile } from "@/lib/types";
import Nav from "@/components/nav";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) redirect("/login");

  // Also doubles as the lazy profile/plot creation trigger for a
  // brand-new user's first visit — the backend creates both on first
  // authenticated request.
  const profile = await apiFetch<Profile>("/profile", session.access_token);

  return (
    <div className="flex min-h-screen flex-col">
      <Nav username={profile.username} />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">{children}</main>
    </div>
  );
}
