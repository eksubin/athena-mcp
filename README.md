# Athena

A job-hunt platform Claude can talk to cheaply: FastAPI + Supabase backend,
a thin MCP layer on top of it, a web app, and a shared world that grows as
you apply. Full design: see the
[Athena Technical Spec](https://claude.ai/code/artifact/8e673e85-7d34-4417-a377-5fbcc2c6b790).

Builds on [eksubin/job-apply-plugin](https://github.com/eksubin/job-apply-plugin)
— that plugin's visible-browser form-filling stays exactly as it is; this
project replaces where its data and search results live.

## Status

**Phases 0-4 are built and verified working end to end against a real
Supabase project**: schema/RLS, the FastAPI backend, the MCP server, the
Next.js web app (dashboard, profile, settings, and a live three.js world),
and an HN ingestion worker. Phase 5 (production hardening) is partially
done — see below.

- `supabase/migrations/0001_init.sql` — full schema + RLS policies
- `backend/` — FastAPI app: profile, resumes, answers, jobs, applications,
  world, personal-access-token endpoints
- `mcp/` — MCP server exposing `search_jobs`, `get_job`, `save_job`,
  `get_queue`, `start_application`, `record_answer`, `update_status`,
  `get_profile`
- `frontend/` — Next.js app: Google sign-in, an application Kanban board,
  profile/resume/answer-bank editing, MCP token management, and a
  three.js render of the shared world with live updates via Supabase
  Realtime
- `worker/` — ingests HN's "Who is hiring?" thread on a schedule (public
  API, no login). LinkedIn/Twitter deliberately stay a human-supervised
  browser flow, not automated — see `worker/README.md` for why
- `docker-compose.yml` — api + web + worker, with a local volume for
  resume files

**Known gaps:**
- CV parsing isn't implemented — resume upload stores the file but doesn't
  extract `profile_facts` from it yet.
- The actual Google OAuth click-through hasn't been verified with a real
  browser (everything around it — routing, redirects, session handling,
  build — has been). Worth a real sign-in test before you trust it fully.
- Phase 5: images are already multi-stage/slim and healthchecked, and
  `docker compose up` runs the full stack locally, but nothing has been
  deployed to an actual VPS yet — that needs a real server target.

## Setup

### 1. Supabase project

Create a project at [supabase.com](https://supabase.com) (Cloud, not
self-hosted — see spec section 07 for why). Enable the Google provider
under Authentication > Providers.

Apply `supabase/migrations/0001_init.sql` and `supabase/seed.sql` via the
SQL Editor in the Supabase dashboard (simplest — no extra credentials
needed), or via the Supabase CLI if you have a personal access token for
it.

From Project Settings > API, grab: **Project URL**, **anon public key**,
**service_role key**, and the **JWT Secret**. Note some newer projects sign
tokens asymmetrically and don't expose a usable legacy secret at all — if
`SUPABASE_JWT_SECRET` doesn't validate a real session token, the backend's
`mint_impersonation_jwt` approach (used for the MCP auth path) won't work
as-is and needs revisiting for that project.

### 2. Backend + web + worker

```sh
cp .env.example .env        # fill in the Supabase values above
docker compose up --build
```

This runs all three services: API on `:8000`, web app on `:3000`, worker
on a loop in the background. `PUBLIC_API_URL` in `.env` should be the
API's real public URL once this isn't just local — the browser calls it
directly, it's baked into the web build at build time.

Without Docker: each of `backend/`, `frontend/`, `worker/`, `mcp/` is
runnable on its own (`uv sync` + `uv run ...` for the Python ones, `npm
install` + `npm run dev` for the frontend — each has its own
`.env.example`).

**Behind a corporate/AV TLS-inspecting proxy?** `docker compose build` may
fail with certificate errors. `docker-compose.override.yml` (gitignored,
not committed) is where a local-only fix lives if you need one — see
`backend/Dockerfile.localdev` for the pattern.

### 3. Sign in and connect the MCP server

Open `http://localhost:3000`, sign in with Google, go to **Settings**, and
create a personal access token. Then:

```sh
cd mcp
cp .env.example .env        # ATHENA_API_URL + the token from above
uv sync
```

Add to Claude Code's MCP config:

```json
{
  "mcpServers": {
    "athena": {
      "command": "uv",
      "args": ["--directory", "mcp", "run", "athena-mcp"]
    }
  }
}
```

## Repo layout

```
supabase/migrations/   schema + RLS policies
supabase/seed.sql       sample jobs for local dev
backend/                FastAPI app (Python, uv)
frontend/               Next.js app (dashboard, profile, settings, world)
worker/                  HN ingestion loop (Python, uv)
mcp/                     MCP server (Python, uv) — runs locally, not in docker-compose
docker-compose.yml       api + web + worker + resumes volume
```
