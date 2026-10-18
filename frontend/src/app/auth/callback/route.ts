import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/dashboard";
  // Not `new URL(request.url).origin` — with HOSTNAME=0.0.0.0 set so the
  // standalone server binds correctly (see frontend/Dockerfile), Next.js
  // also uses that value when it reconstructs a Route Handler's request
  // URL, instead of the browser's actual Host header. Same fix as the
  // login page: use the one fixed, correct origin instead of trusting
  // anything derived from the request.
  const origin = process.env.NEXT_PUBLIC_SITE_URL ?? new URL(request.url).origin;

  // A refused sign-up never reaches the code exchange: GoTrue bounces
  // straight back here with its own error, which for this app almost
  // always means the invite gate turned the address away.
  const providerError = searchParams.get("error_description") ?? searchParams.get("error");
  if (providerError && !code) {
    console.error("auth callback returned a provider error:", providerError);
    const refusedBySignupGate = /database error (saving|creating) new user/i.test(providerError);
    return NextResponse.redirect(
      `${origin}/login?error=${refusedBySignupGate ? "invite" : "auth"}`,
    );
  }

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${origin}${next}`);
    }
    console.error("exchangeCodeForSession failed:", error.status, error.message);
  } else {
    console.error("auth callback hit with no ?code param:", request.url);
  }

  return NextResponse.redirect(`${origin}/login?error=auth`);
}
