# Deploying Athena

This covers taking the stack from "running locally via `docker compose up`"
to a real VPS with a real domain and real HTTPS. Everything here is written
against `docker-compose.prod.yml` + `Caddyfile`, both already in the repo —
neither has been exercised against a real server yet, since building this
didn't have one to deploy to. Caddy's automatic-HTTPS behavior is
well-established, but treat the first real run as a first real run.

For a full walkthrough on AWS EC2 with a GoDaddy domain, including a
script that writes `.env` and a troubleshooting section, see
[DEPLOYMENT.md](DEPLOYMENT.md).

## 1. Prerequisites

- A VPS with Docker + Docker Compose installed, and ports 80/443 open
- Three DNS A records pointing at the VPS's IP: the app
  (`athena.yourdomain.com`), the API (`api.yourdomain.com`), and the
  Supabase gateway (`db.yourdomain.com`, or similar) — Caddy needs all
  three to exist and resolve *before* it starts, so it can get
  certificates for them
- The same self-hosted-Supabase values already in your local `.env`
  (`POSTGRES_PASSWORD`, `JWT_SECRET`, `ANON_KEY`, `SERVICE_ROLE_KEY`)

## 2. Update Google for the real domain

**Google Cloud Console → your OAuth client → Authorized redirect URIs**:
add `https://db.yourdomain.com/auth/v1/callback` (the gateway domain, not
the app domain — GoTrue's own callback, not the frontend's). The
`localhost:8001` one from local dev can stay too if you still develop
locally against the same Google client.

The production overlay derives the authentication URLs and Google callback
from `ATHENA_DB_DOMAIN`, and the app callback from `ATHENA_DOMAIN`.

## 3. Configure the server

```sh
git clone <this repo> athena && cd athena
cp .env.example .env
```

Fill in `.env` with real values for everything (generate fresh
`POSTGRES_PASSWORD`/`JWT_SECRET`/`ANON_KEY`/`SERVICE_ROLE_KEY` for this
deployment — don't reuse local dev's), plus:

```sh
PUBLIC_API_URL=https://api.yourdomain.com
PUBLIC_SUPABASE_URL=https://db.yourdomain.com
PUBLIC_SITE_URL=https://athena.yourdomain.com
API_EXTERNAL_URL=https://db.yourdomain.com/auth/v1
ATHENA_DOMAIN=athena.yourdomain.com
ATHENA_API_DOMAIN=api.yourdomain.com
ATHENA_DB_DOMAIN=db.yourdomain.com
```

The production overlay requires all three `ATHENA_*_DOMAIN` values and
derives frontend build URLs, authentication redirects, and API CORS from
them. It overrides local development URLs, disables the test-login form
and endpoint, and disables email/password authentication. Rebuild the web
image after changing domains because browser URLs are embedded at build time.

## 4. Bring it up

```sh
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

This adds `caddy` (automatic HTTPS via Let's Encrypt, no manual cert
handling) and stops publishing `api`/`web`/`gateway`'s ports directly —
only Caddy is internet-facing, everything else talks over the compose
network. First boot takes a little longer while Caddy requests
certificates and `db` runs its init scripts; watch both with
`docker compose logs -f caddy db`.

Once `db` is healthy, apply the schema the same way as local dev:

```sh
docker exec -i athena-db-1 psql -U postgres -d postgres < supabase/migrations/0001_init.sql
docker exec -i athena-db-1 psql -U postgres -d postgres < supabase/migrations/0002_invites_and_admin.sql
docker exec -i athena-db-1 psql -U postgres -d postgres < supabase/migrations/0003_profile_identity.sql
docker exec -i athena-db-1 psql -U postgres -d postgres < supabase/seed.sql
```

**Set the first administrator's address in `0002_invites_and_admin.sql`
before applying it.** Athena is invite-only — accounts can only be created
for addresses somebody inside has invited — and that migration leaves one
pending admin invite, which is the only way into `/admin` on a fresh
deployment. Signing in on that address makes you an administrator; roles,
invite allowances and access are managed from the panel after that.

## 5. After it's up

- `https://athena.yourdomain.com` should serve the app; `/health` on the
  API domain should return `{"status": "ok"}`; `/auth/v1/health` on the
  db domain should return GoTrue's version info
- Issue yourself an MCP personal access token from `/settings`, same as
  local dev, then point the MCP server's `ATHENA_API_URL` at
  `https://api.yourdomain.com`
- `docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f`
  for all services; Caddy's logs are the place to look if HTTPS itself
  isn't coming up (usually a DNS record that hasn't propagated yet)

## Updating

```sh
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Caddy's certificates persist in the `caddy_data` volume, so this doesn't
re-trigger Let's Encrypt rate limits on every deploy.
