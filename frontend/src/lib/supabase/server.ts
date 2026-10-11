import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { SUPABASE_COOKIE_NAME } from "./cookie-name";

// Same split as frontend/src/lib/api.ts's SERVER_API_URL: this runs inside
// the `web` container, where the self-hosted Supabase gateway is a sibling
// container (`gateway:8001`), not reachable at the browser-facing
// NEXT_PUBLIC_SUPABASE_URL (`localhost:8001` means the web container
// itself from here). SUPABASE_INTERNAL_URL is deliberately not NEXT_PUBLIC_.
const SUPABASE_URL = process.env.SUPABASE_INTERNAL_URL ?? process.env.NEXT_PUBLIC_SUPABASE_URL!;

export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    SUPABASE_URL,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookieOptions: { name: SUPABASE_COOKIE_NAME },
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            );
          } catch {
            // Called from a Server Component render — middleware is what
            // actually refreshes the session cookie on the next request.
          }
        },
      },
    },
  );
}
