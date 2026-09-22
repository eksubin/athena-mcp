"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const [pending, setPending] = useState(false);

  async function handleSignIn() {
    setPending(true);
    const supabase = createClient();
    // Deliberately not window.location.origin — that's whatever happens to
    // be in the address bar (0.0.0.0, a LAN IP, a stale bookmark...), and
    // Google/Supabase would faithfully send the user back to exactly that,
    // even if it's not reachable. This is the one fixed, known-good origin.
    const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? window.location.origin;
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${siteUrl}/auth/callback` },
    });
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 bg-stone-50 px-4">
      <div className="text-center">
        <h1 className="text-3xl font-semibold tracking-tight text-stone-900">Athena</h1>
        <p className="mt-2 text-stone-600">
          Track what you&apos;ve saved, applied to, and heard back on — and watch your
          territory grow while you do it.
        </p>
      </div>
      <button
        onClick={handleSignIn}
        disabled={pending}
        className="rounded-full bg-stone-900 px-6 py-3 text-sm font-medium text-white transition hover:bg-stone-700 disabled:opacity-60"
      >
        {pending ? "Redirecting…" : "Continue with Google"}
      </button>
    </main>
  );
}
