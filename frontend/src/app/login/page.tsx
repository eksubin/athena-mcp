"use client";
import Link from "next/link";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Brand, Icon } from "@/components/ui";

const TEST_LOGIN_ENABLED = process.env.NEXT_PUBLIC_ENABLE_TEST_LOGIN === "true";
export default function LoginPage() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  async function handleGoogleSignIn() {
    setPending(true);
    setError("");
    try {
      const siteUrl =
        process.env.NEXT_PUBLIC_SITE_URL ?? window.location.origin;
      const { error: signInError } = await createClient().auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: `${siteUrl}/auth/callback` },
      });
      if (signInError) throw signInError;
    } catch {
      setError(
        "Google sign-in is unavailable right now. Please try again later.",
      );
      setPending(false);
    }
  }
  return (
    <main className="login-page">
      <section className="login-story">
        <Link href="/" aria-label="Athena home">
          <Brand />
        </Link>
        <div className="login-story-copy">
          <p className="eyebrow">A calmer way to find what’s next</p>
          <h1>
            Your next chapter
            <br />
            starts with
            <br />a little clarity.
          </h1>
          <p>
            Bring your opportunities, your experience, and your progress into
            one thoughtful space.
          </p>
          <div className="journey-card">
            <div className="journey-header">
              <span>Room for every next step</span>
              <Icon name="briefcase" size={18} />
            </div>
            <div className="journey-track" aria-hidden="true">
              <span />
              <span />
              <span />
              <span />
            </div>
            <div className="journey-labels">
              <span>Discover</span>
              <span>Apply</span>
              <span>Connect</span>
              <span>Grow</span>
            </div>
            <div className="journey-footer">
              <Icon name="shield" size={16} />
              <span>
                Invite-only. Your search is personal, your details stay
                private.
              </span>
            </div>
          </div>
        </div>
        <p className="login-story-footer">
          A little more intention. A little less overwhelm.
        </p>
      </section>
      <section className="login-form-side">
        <div className="login-form">
          <Link href="/" aria-label="Athena home">
            <Brand />
          </Link>
          <p className="eyebrow">Welcome to your workspace</p>
          <h2>Let’s find your next.</h2>
          <p>Sign in to pick up your search and keep moving forward.</p>
          <Suspense fallback={null}>
            <SignInNotice />
          </Suspense>
          <button
            className="button button-primary button-full"
            disabled={pending}
            onClick={handleGoogleSignIn}
          >
            {pending ? "Connecting…" : "Continue with Google"}
            <Icon name="arrow" size={16} />
          </button>
          {error && (
            <p role="alert" className="form-error" style={{ marginTop: 16 }}>
              {error}
            </p>
          )}
          <div className="login-privacy">
            Athena is invite-only — sign in with the address you were invited
            on.
            <br />
            Your resume, answers, and applications stay private. Only your
            chosen username appears in the shared world.
          </div>
          {TEST_LOGIN_ENABLED && <TestLogin />}
          <Link
            className="test-login-toggle"
            style={{ display: "block", marginTop: 24 }}
            href="/"
          >
            Back to Athena
          </Link>
        </div>
      </section>
    </main>
  );
}

/** What the door says when something went wrong on the way in.
 *
 * GoTrue cannot tell the browser *why* a sign-up was refused — the invite
 * gate lives in the database, so a refused account surfaces as a generic
 * server error (see supabase/migrations/0002_invites_and_admin.sql). The
 * honest reading of that error, for an app where registration is closed,
 * is "this address has not been invited", so that is what it says — while
 * `access` (an account whose access was withdrawn) and `auth` (a genuine
 * sign-in failure) stay distinct.
 */
function SignInNotice() {
  const reason = useSearchParams().get("error");
  if (!reason) return null;
  const message =
    reason === "invite"
      ? "Athena is invite-only, and this address hasn’t been invited yet. Ask whoever invited you to add this exact address."
      : reason === "access"
        ? "This account’s access to Athena has been withdrawn. Contact an administrator if you think that’s a mistake."
        : "We couldn’t complete that sign-in. Please try again.";
  return (
    <p className="form-error" role="alert" style={{ margin: "0 0 18px" }}>
      {message}
    </p>
  );
}

function TestLogin() {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<"in" | "up" | null>(null);
  async function submit(action: "in" | "up") {
    setBusy(action);
    setError("");
    try {
      const res = await fetch("/auth/test-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, action }),
      });
      if (!res.ok) {
        const body = await res
          .json()
          .catch(() => ({ error: "Sign-in failed. Please try again." }));
        setError(body.error ?? "Sign-in failed. Please try again.");
        setBusy(null);
        return;
      }
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.href = "/dashboard";
    } catch {
      setError("We couldn’t reach Athena. Please try again.");
      setBusy(null);
    }
  }
  return (
    <div className="test-login">
      {!open ? (
        <button className="test-login-toggle" onClick={() => setOpen(true)}>
          Test login · No Google account needed
        </button>
      ) : (
        <form
          className="form-stack"
          onSubmit={(e) => {
            e.preventDefault();
            void submit("in");
          }}
        >
          <p className="eyebrow">Local test workspace</p>
          <label className="field">
            <span className="field-label">Email address</span>
            <input
              className="input"
              required
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </label>
          <label className="field">
            <span className="field-label">Password</span>
            <input
              className="input"
              required
              type="password"
              minLength={6}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 6 characters"
            />
          </label>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <div className="test-login-actions">
            <button
              className="button button-primary"
              disabled={busy !== null}
              type="submit"
            >
              {busy === "in" ? "Signing in…" : "Sign in"}
            </button>
            <button
              className="button button-secondary"
              disabled={busy !== null || !email || password.length < 6}
              type="button"
              onClick={() => submit("up")}
            >
              {busy === "up" ? "Creating…" : "Create account"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
