# Athena

An invite-only job-hunt platform Claude can talk to cheaply: FastAPI + a
self-hosted Supabase stack, a thin MCP layer on top of it, a web app, and
a shared world that grows as you apply. Full design: see the
[Athena Technical Spec](https://claude.ai/code/artifact/8e673e85-7d34-4417-a377-5fbcc2c6b790).

Builds on [eksubin/job-apply-plugin](https://github.com/eksubin/job-apply-plugin)
— that plugin's visible-browser form-filling stays exactly as it is; this
project replaces where its data and search results live.

## Status

**All five phases are built, and the whole stack — including a real Google
sign-in — has been exercised end to end, not just unit-tested.**

Originally built against Supabase Cloud; migrated to self-hosting
Supabase's own db/auth/rest (see "Why self-hosted Supabase" below) after
its free tier auto-paused the project and took the whole app down with it.

- `supabase/migrations/0001_init.sql` — full schema + RLS policies
- `supabase/docker/`, `supabase/gateway/` — the self-hosted stack's init
  SQL and routing config (see docker-compose.yml's `db`/`auth`/`rest`/`gateway`)
- `backend/` — FastAPI app: profile (+ extracted resume facts), resumes,
  answers, jobs, applications, world, personal-access-token endpoints
- [athena-mcp](https://github.com/eksubin/Athena) — the MCP server, in
  its own repository: ten tools (`track_job`, `search_jobs`, `get_job`,
  `save_job`, `get_queue`, `start_application`, `record_answer`,
  `update_status`, `get_profile`, `import_linkedin_job`). It runs on each
  user's own machine, not in this stack, so it installs from git with
  `uvx` and nothing to check out. The API surface between the two repos is
  versioned — `backend/app/core/contract.py` and that repo's `CONTRACT.md`.
  (The `mcp/` tree here is that repository's prepared state, waiting to be
  moved across; delete this bullet's parenthesis and the tree once it has.)
- `frontend/` — Next.js app: public landing page, Google sign-in, an application board/list view,
  profile/resume/answer-bank editing (resumes get parsed into structured
  facts on upload), MCP token management, and a three.js render of the
  shared world. While visible, the world refreshes every 15 seconds;
  Supabase Realtime is not required.
- `worker/` — ingests HN's "Who is hiring?" thread on a schedule (public
  API, no login). LinkedIn/Twitter deliberately stay a human-supervised
  browser flow, not automated — see `worker/README.md` for why
- `docker-compose.yml` — db + auth + rest + gateway + api + web + worker,
  local dev; `docker-compose.prod.yml` + `Caddyfile` add automatic HTTPS
  for a real deploy — see `DEPLOY.md`

### Why self-hosted Supabase

Supabase Cloud's free tier auto-pauses a project after about a week of
inactivity, and a paused project's hostname can stop resolving in DNS
entirely — which looks exactly like a Docker networking bug (and cost a
long debugging session before the actual cause turned up: public DNS
resolvers agreeing the hostname didn't exist, not a local/Docker issue at
all). Fix: self-host the three Supabase services this app actually
uses — Postgres, GoTrue (auth), PostgREST (rest) — behind a small Caddy
gateway standing in for Kong. Nearly all application code is unchanged;
RLS policies still use `auth.uid()`, the backend/frontend still talk to it
through the same `supabase-py`/`@supabase/ssr` clients. Realtime is left
out on purpose — self-hosting it needs per-tenant provisioning that isn't
worth the complexity for one nice-to-have.

Images: `athena-api` ~190MB, `athena-web` ~300MB, `athena-worker` ~150MB —
no browser/Playwright bloat anywhere, since LinkedIn/Twitter search stays
in the existing human-supervised flow. The Supabase pieces (`db`, `auth`,
`rest`, `gateway`) use upstream images as-is, not built by this repo.

**Real bugs this surfaced, roughly in the order they showed up** (kept here
because they're the kind that resurface if this project's patterns get
reused elsewhere):
- `postgrest-py`'s `.maybe_single().execute()` returns `None` outright on
  zero rows, not a response object with `.data = None`
- A Server Component's `fetch` runs *inside the web container*, so
  `NEXT_PUBLIC_API_URL=localhost:8000` (correct for the browser) is wrong
  there — needed a separate, non-public `API_INTERNAL_URL` pointed at the
  API's Docker service name
- `window.location.origin` is whatever's in the address bar, not
  necessarily the app's real URL — both the OAuth `redirectTo` and the
  callback route's own redirect needed a fixed `NEXT_PUBLIC_SITE_URL`
  instead
- Setting `HOSTNAME=0.0.0.0` (so Next's standalone server actually binds
  to all interfaces — Docker auto-injects `HOSTNAME` as the container ID
  otherwise) also changes what Next.js reports as the incoming request's
  origin inside Route Handlers
- A token *self-minted* with what looked like Supabase's JWT secret being
  accepted by PostgREST does not mean that's how *real* GoTrue sessions
  are signed — Supabase *Cloud*'s GoTrue signed real sessions ES256/JWKS,
  verified by decoding an actual issued token's header, not by continuing
  to trust the earlier test. (This stopped mattering once self-hosted —
  see below — but cost real time to pin down while still on Cloud.)
- Docker named volumes are root-owned by default; the app containers run
  as a non-root user, so the volume needs its mountpoint pre-created with
  the right ownership in the image before Docker initializes it
- `postgrest-py`'s `.maybe_single().execute()` bug above isn't the only
  place a `None`-vs-exception assumption breaks: a retry loop that catches
  bare `Exception` to handle "username collision" also silently swallowed
  an unrelated foreign-key error, then proceeded as if the retried insert
  had succeeded — narrow what you catch to the actual error you're
  handling (Postgres error code `23505`, specifically), not everything
  that could go wrong in that block
- Self-hosted GoTrue configured with only `GOTRUE_JWT_SECRET` (no
  asymmetric signing keys) signs real sessions HS256 — so the Cloud-era
  JWKS/ES256 verification above had to come back out; both the web
  session path and the MCP impersonation path now share one HS256
  verification, which is simpler than Cloud's setup, not just different
- Supabase Cloud's free-tier pause can make a project's own hostname stop
  resolving in *public* DNS, not just fail to respond — `nslookup` against
  8.8.8.8/1.1.1.1 directly (bypassing the local router entirely) is what
  actually proved this wasn't a Docker/network-local problem, after a
  Docker-networking theory looked plausible for a while because three
  different containers failed the same way at once

## Setup

### 1. Generate secrets

```sh
cp .env.example .env
```

Fill in `POSTGRES_PASSWORD` and `JWT_SECRET` with any long random strings,
then derive `ANON_KEY`/`SERVICE_ROLE_KEY` from `JWT_SECRET` — they're
just legacy-format Supabase API keys, i.e. a JWT signed with `JWT_SECRET`
containing `{"role": "anon" | "service_role", "iss": "supabase"}`:

```sh
cd backend && uv run python -c "
import jwt, time
secret = 'paste-your-JWT_SECRET-here'
now = int(time.time())
for role in ('anon', 'service_role'):
    print(role, '=', jwt.encode(
        {'role': role, 'iss': 'supabase', 'iat': now, 'exp': now + 10*365*24*3600},
        secret, algorithm='HS256',
    ))
"
```

Put `ANON_KEY`/`SERVICE_ROLE_KEY` in `.env`, and the same two values again
under `SUPABASE_ANON_KEY`/`SUPABASE_SERVICE_ROLE_KEY` (the backend reads
those names), with `SUPABASE_JWT_SECRET` set to the same `JWT_SECRET`.

### 2. Google OAuth

Reuse an existing Google Cloud Console OAuth client, or create one, then
add this to its **Authorized redirect URIs**:
`http://localhost:8001/auth/v1/callback` (swap in your real domain for a
real deploy — see `DEPLOY.md`). Put the client ID/secret in `.env` as
`GOOGLE_CLIENT_ID`/`GOOGLE_SECRET`.

### 3. Bring up the stack

```sh
docker compose up --build
```

This brings up seven services: the self-hosted Supabase stack
(`db`, `auth`, `rest`, `gateway` — the last on `:8001`), then `api`
(`:8000`), `web` (`:3000`), and `worker`. First boot takes longer while
`db` runs its init scripts. Once `db` reports healthy, apply the schema:

```sh
docker exec -i athena-db-1 psql -U postgres -d postgres < supabase/migrations/0001_init.sql
docker exec -i athena-db-1 psql -U postgres -d postgres < supabase/migrations/0002_invites_and_admin.sql
docker exec -i athena-db-1 psql -U postgres -d postgres < supabase/migrations/0003_profile_identity.sql
docker exec -i athena-db-1 psql -U postgres -d postgres < supabase/seed.sql
```

**Before applying `0002`, set the first administrator's address in it.**
Athena is invite-only: an account can only be created for an address that
somebody already inside has invited, enforced by a trigger on `auth.users`
rather than in the API, so it covers Google sign-in and the local test
login alike. That migration grandfathers any accounts that already exist
and leaves one pending **admin** invite — the only way into `/admin` on a
fresh deployment. Everything after that is managed from the panel.

`PUBLIC_API_URL`/`PUBLIC_SUPABASE_URL`/`PUBLIC_SITE_URL` in `.env` should
be real public URLs once this isn't just local — the browser calls them
directly, and they're baked into the web build at build time. For an
actual deploy with real HTTPS, see `DEPLOY.md` instead of plain
`docker compose up`.

Without Docker: each of `backend/`, `frontend/`, `worker/` is runnable on
its own (`uv sync` + `uv run ...` for the Python ones, `npm install` +
`npm run dev` for the frontend — each has its own `.env.example`). The MCP
server always runs outside the stack, wherever the assistant does.

**Behind a corporate/AV TLS-inspecting proxy?** `docker compose build` may
fail with certificate errors. `docker-compose.override.yml` (gitignored,
not committed) is where a local-only fix lives if you need one — see
`backend/Dockerfile.localdev` for the pattern.

### 4. Sign in and connect an assistant

Open `http://localhost:3000` and sign in with Google using the address you
set as the first administrator. Go to **Settings** and create a personal
access token.

The MCP server is not part of this stack — it's a separate package,
[athena-mcp](https://github.com/eksubin/Athena), that runs on the
machine the assistant runs on. Nothing to check out:

```json
{
  "mcpServers": {
    "athena": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/eksubin/Athena", "athena-mcp"],
      "env": {
        "ATHENA_API_URL": "http://localhost:8000",
        "ATHENA_TOKEN": "athena_pat_..."
      }
    }
  }
}
```

That repository's README covers Codex, the ten tools and the review-only
walkthrough. Athena prepares and tracks applications; only the employer's
browser form actually submits one.

### 5. Make the profile yours

**My profile → How you appear** is where the username and avatar other
people see in the shared world are chosen. Neither is your real name;
the resume, answers and applications behind them stay private.

### 6. Invite other people

Athena never emails anyone. Invite an address from **My profile → Invite
someone in** (every member gets three invites by default) or from
**Administration → Invites**, then send that person the link yourself. The
`/admin` panel manages roles, invite allowances and access; withdrawing
access suspends the account without deleting any of its data.

## Using it

[USER-GUIDE.md](USER-GUIDE.md) is written for the people who will actually
use the thing: getting in, setting up a profile, the pipeline, connecting an
assistant, the shared world, invites, and what the administration panel does.

## Verification

With the local Docker stack running, run the disposable-account integration
check from PowerShell at the repository root:

```powershell
Get-Content -Raw scripts/smoke_test.py | docker compose exec -T api python -
```

It checks the API, resume parsing, world growth, token revocation,
one-call job tracking, and authenticated web pages. Registration is
closed, so it allowlists its disposable address before creating it, and
deletes the account, its invite, its jobs and its uploaded file
afterwards.

The other half — all ten MCP tools over stdio, against this deployment —
lives with the client, in athena-mcp's `scripts/smoke_test.py`. It takes
the deployment from the environment, so run it from that checkout with
`SUPABASE_SERVICE_ROLE_KEY` and `SUPABASE_JWT_SECRET` from this `.env`
exported. It is the executable half of the cross-repo contract: run it
after changing anything athena-mcp calls.

Run `uv run pytest` in `backend/` and `worker/`, and `npm run lint` plus
`npm run build` in `frontend/`. On Windows, if Turbopack exits while
starting its CSS worker, use `npm run build:webpack`; the Docker build
can continue to use Turbopack.

Google OAuth requires `GOOGLE_CLIENT_ID` and `GOOGLE_SECRET` in `.env`
and the callback URL configured in Google Cloud. Local test login works
without these. The world polls for updates while visible instead of
connecting to the unsupported Supabase Realtime service.

## Repo layout

```
supabase/migrations/    schema + RLS policies
supabase/seed.sql        sample jobs for local dev
supabase/docker/         db init SQL for the self-hosted stack (roles, jwt)
supabase/gateway/        Caddyfile routing /auth/v1 + /rest/v1 to auth/rest
backend/                 FastAPI app (Python, uv)
frontend/                Next.js app (dashboard, profile, settings, world, admin)
worker/                  HN ingestion loop (Python, uv)
mcp/                     prepared state of the separate athena-mcp repository — see above
docker-compose.yml       db + auth + rest + gateway + api + web + worker, local dev
docker-compose.prod.yml  + Caddyfile — adds automatic HTTPS, see DEPLOY.md
DEPLOY.md                taking this to a real VPS with a real domain
```
