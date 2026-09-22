// This runs in two very different places, and one URL can't be right for
// both: in a Server Component it executes inside the `web` container
// itself, where the API is a *sibling* container reachable at its Docker
// service name — `localhost` there means the web container, not the API.
// In a Client Component it runs in the browser on the host machine, where
// `localhost` correctly reaches the API's mapped port. API_INTERNAL_URL is
// deliberately not NEXT_PUBLIC_ — it must never end up in the client
// bundle, and being a plain server env var means it's read fresh at
// request time rather than baked in at build time.
const SERVER_API_URL =
  process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const CLIENT_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function apiFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const base = typeof window === "undefined" ? SERVER_API_URL : CLIENT_API_URL;
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      // Skip when the body is FormData — the browser needs to set its own
      // multipart boundary in that case, so we must not override it.
      ...(init?.body && !(init.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...init?.headers,
    },
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${init?.method ?? "GET"} ${path} failed (${res.status}): ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
