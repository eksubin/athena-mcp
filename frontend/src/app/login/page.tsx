"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

// Dev/prototyping convenience — sign in with a plain email+password instead
// of the full Google OAuth handshake, which needs a real browser capable of
// completing it. Disable for a real public deploy by unsetting this.
const TEST_LOGIN_ENABLED = process.env.NEXT_PUBLIC_ENABLE_TEST_LOGIN === "true";

export default function LoginPage() {
  const [pending, setPending] = useState(false);

  async function handleGoogleSignIn() {
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
        onClick={handleGoogleSignIn}
        disabled={pending}
        className="rounded-full bg-stone-900 px-6 py-3 text-sm font-medium text-white transition hover:bg-stone-700 disabled:opacity-60"
      >
        {pending ? "Redirecting…" : "Continue with Google"}
      </button>

      {TEST_LOGIN_ENABLED && <TestLogin />}
    </main>
  );
}

function TestLogin() {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"in" | "up" | null>(null);

  async function submit(action: "in" | "up") {
    setBusy(action);
    setError(null);
    // Routed through a server-side handler rather than calling
    // supabase.auth.signInWithPassword/signUp directly from here — see
    // auth/test-login/route.ts for why that matters (the short version:
    // the session cookie only gets set reliably on the server side).
    const res = await fetch("/auth/test-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, action }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({ error: "Something went wrong." }));
      setError(body.error ?? "Something went wrong.");
      setBusy(null);
      return;
    }
    // A full navigation, not router.push — guarantees a fresh request
    // through the middleware with the cookie the route handler just set,
    // rather than relying on the client router's own transition.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = "/dashboard";
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="text-xs text-stone-400 underline-offset-2 hover:text-stone-600 hover:underline"
      >
        Test login (no Google needed)
      </button>
    );
  }

  return (
    <div className="flex w-full max-w-xs flex-col gap-2 rounded-lg border border-stone-200 bg-white p-4">
      <p className="mb-1 text-center text-[11px] tracking-wide text-stone-400 uppercase">
        Prototyping only — not for real accounts
      </p>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="any@email.works"
        className="rounded-md border border-stone-300 px-3 py-2 text-sm"
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="password (6+ characters)"
        className="rounded-md border border-stone-300 px-3 py-2 text-sm"
      />
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button
          onClick={() => submit("in")}
          disabled={busy !== null}
          className="flex-1 rounded-md bg-stone-900 px-3 py-2 text-xs font-medium text-white hover:bg-stone-700 disabled:opacity-60"
        >
          {busy === "in" ? "Signing in…" : "Sign in"}
        </button>
        <button
          onClick={() => submit("up")}
          disabled={busy !== null}
          className="flex-1 rounded-md border border-stone-300 px-3 py-2 text-xs font-medium text-stone-700 hover:bg-stone-50 disabled:opacity-60"
        >
          {busy === "up" ? "Creating…" : "Create test account"}
        </button>
      </div>
    </div>
  );
}
