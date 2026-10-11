// @supabase/ssr defaults to deriving the session cookie's name from the
// Supabase URL's hostname (e.g. "sb-gateway-auth-token" vs
// "sb-localhost-auth-token"). The browser client and the server-side
// clients deliberately use *different* URLs — gateway:8001 internally,
// localhost:8001 for the browser — so left on defaults, the server would
// never find the cookie the browser actually set. Pinning one fixed name
// here, used by every createBrowserClient/createServerClient call,
// decouples the cookie name from which URL variant is in play.
export const SUPABASE_COOKIE_NAME = "sb-athena-auth-token";
