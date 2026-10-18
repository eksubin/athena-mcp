import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

// Dev/prototyping only (see login/page.tsx) — the sign-in itself has to
// happen in a Route Handler, not called straight from the Client
// Component: @supabase/ssr's cookie `setAll` is a documented no-op during
// a Server Component render, and only reliably writes the session cookie
// in a context like this one. Doing it client-side left the cookie
// inconsistently set, which is why the post-login redirect kept bouncing
// back to /login — the middleware's session check never saw a session.
export async function POST(request: Request) {
  if (process.env.NEXT_PUBLIC_ENABLE_TEST_LOGIN !== "true") {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }
  const { email, password, action } = await request.json();
  if (typeof email !== "string" || typeof password !== "string") {
    return NextResponse.json({ error: "email and password are required" }, { status: 400 });
  }

  const supabase = await createClient();
  const { error } =
    action === "up"
      ? await supabase.auth.signUp({ email, password })
      : await supabase.auth.signInWithPassword({ email, password });

  if (error) {
    return NextResponse.json({ error: signInMessage(error.message) }, { status: 400 });
  }
  return NextResponse.json({ ok: true });
}

// The invite gate is a database trigger, so GoTrue reports a refused
// sign-up as a generic save failure. Registration being closed, that is
// what it almost always means here — say so instead of passing on an
// internal-sounding error.
function signInMessage(message: string) {
  if (/database error (saving|creating) new user/i.test(message))
    return "Athena is invite-only. This address hasn’t been invited yet.";
  return message;
}
