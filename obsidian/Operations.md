# Operations

[[Home]] · [[Architecture]] · [[Local Setup]]

## Deployment

Follow [DEPLOY.md](../DEPLOY.md). That guide states the production configuration had not been exercised on a real server when written; these notes do not establish deployment verification.

Provision Docker, ports 80/443, and app/API/gateway DNS records. Configure production public URLs, CORS, Google's gateway callback, and deployment-specific secrets.

```sh
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

The overlay enables Caddy HTTPS and disables test login UI and GoTrue email authentication. Rebuild web after public frontend settings change. Initialize the schema for a fresh database — `0001_init.sql`, `0002_invites_and_admin.sql` (with the first administrator's address set) and `0003_profile_identity.sql`, in that order; sample seed jobs are optional.

This checkout has a local docker-compose.override.yml for TLS-inspection-specific Dockerfiles. Plain Compose commands can auto-load it. Explicit -f commands select the intended production files.

## Verification and development

Check Compose status and logs. API /health returns a basic status, not a full dependency check. Gateway /auth/v1/health checks GoTrue. Exercise sign-in, resume upload, status changes, and a token-authenticated MCP request to verify integrated behavior.

Both smoke scripts allowlist their disposable address before creating it and remove the invite afterwards; a signup that fails with `Database error saving new user` means an address was not allowlisted first.

Run uv run pytest separately in backend and worker. Existing tests cover scoring, resume parsing, world placement, HN parsing, and LinkedIn capture parsing. For frontend changes, run npm run lint and npm run build. Application tests were not run for this documentation-only addition.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Server-rendered API calls fail | API_INTERNAL_URL must use Docker service address, not browser localhost |
| Browser cannot reach services | Public URLs must be browser-reachable; rebuild public build arguments |
| Wrong OAuth return address | PUBLIC_SITE_URL, GoTrue allow list, Google gateway callback |
| JWT rejected | Matching signing secret and derived keys; self-hosted sessions use HS256 |
| Missing-row lookup crashes | maybe_single().execute() can return None outright |
| Sign-up refused as a server error | Address has no live invite; GoTrue cannot report the reason |
| Signed-in user bounced to /login?error=access | Account suspended; restore it from /admin |
| /admin unreachable after a fresh deploy | First administrator's address not set in migration 0002 |
| A chosen username is refused | Shape rule, a reserved handle, or another account holds it |
| Resume file writes fail | Volume mountpoint ownership for non-root API user |
| World appears stale | Refresh; Realtime is not configured |
| Local build certificate errors | Localdev Dockerfile and override pattern |
| First HTTPS deploy fails | DNS, ports 80/443, Caddy logs |

Persisted state lives in db_data, resumes, and production Caddy volumes. Back up database and resumes together according to deployment recovery needs. Removing volumes can destroy data.

Sources: [README](../README.md), [production overlay](../docker-compose.prod.yml), [deployment guide](../DEPLOY.md).
