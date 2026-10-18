# Going live

[[Home]] · [[Operations]] · [[Local Setup]] · [[Architecture]]

Planning notes for the move off this machine: picking a host, what bites
during the first deploy, and splitting the MCP server into its own
repository. [[Operations]] covers running the stack once it is up; this note
covers the decisions taken before that.

Decisions recorded here were taken on 2026-10-18 and are not yet carried
out. Nothing has been deployed and the repository still has no git remote.

## Picking a host

The deciding factors for this stack are memory and CPU architecture, because
it runs seven containers including Postgres.

| | Oracle Cloud | AWS |
| --- | --- | --- |
| Free option | Ampere A1, up to 4 OCPU / 24 GB, always free | 12 months of `t3.micro`, 1 GB |
| Fits the stack? | Comfortably | No — 1 GB is below what it needs |
| Realistic paid shape | — | `t4g.small` (arm64) or `t3.small` |
| Catch | A1 capacity is often unavailable; arm64 | Costs money from the start |

Steady state is roughly 700 MB–1 GB across all seven containers. **2 GB is
comfortable; 1 GB is not.**

### The arm64 question

Both the Oracle free shape and AWS's cheapest usable shape are arm64. The
three images built here descend from multi-arch Python and Node bases, so
the question is only about the four pinned images. Check before committing
to an ARM host:

```sh
for i in supabase/postgres:17.6.1.136 supabase/gotrue:v2.196.0 \
         postgrest/postgrest:v14.17 caddy:2-alpine; do
  echo "$i"
  docker manifest inspect "$i" | grep -o '"architecture": "[^"]*"' | sort -u
done
```

### Building on a small instance

`next build`, which runs inside `docker compose build` for the `web`
service, needs considerably more memory than the stack does at rest and will
be killed on a small box. Either add swap before the first build, or build
the images elsewhere and push them to a registry.

## First-deploy traps

[DEPLOY.md](../DEPLOY.md) is the procedure. These are the parts that fail
quietly or fail late:

| Trap | Why |
| --- | --- |
| All three DNS records must resolve **before** Caddy starts | It requests certificates for app, API and gateway on startup; a missing record fails issuance for all of them |
| `NEXT_PUBLIC_*` are build arguments | Changing domains in `.env` does nothing until `web` is rebuilt — the old address stays baked into the browser bundle |
| Migrations run in order: 0001, 0002, 0003 | And the first administrator's address goes into `0002` *before* applying it, or nothing can reach /admin — see [[Invites and Administration]] |
| Google's redirect URI is the **gateway** domain | `https://db.yourdomain.com/auth/v1/callback`, not the app domain — see [[Google Sign-in]] |
| Back up `db_data` and `resumes` together | A database referencing resume files that are not there is worse than having neither |

## Splitting out the MCP server

The MCP server moves to its own repository. The web stack stays here.

### Why

Athena is invite-only, so every new user was personally invited — but
connecting an assistant currently means obtaining a copy of this repository,
installing `uv`, running `uv sync`, and putting an absolute path into a
client config. That is a developer-grade install to hand someone who was
just invited.

With its own repository the whole of a new user's configuration becomes:

```json
{"mcpServers": {"athena": {
  "command": "uvx",
  "args": ["--from", "git+https://github.com/<owner>/athena-mcp", "athena-mcp"],
  "env": {"ATHENA_API_URL": "https://api.<domain>",
          "ATHENA_TOKEN": "athena_pat_..."}}}}
```

No checkout, no sync, no paths. Publishing to a registry is unnecessary once
the repository is reachable.

### What makes it feasible

`mcp/` is already close to standalone: its own `pyproject.toml` with the
`athena-mcp` console script, `uv.lock`, package, tests and README. The only
reference it makes outside itself is `config.py` resolving
`parents[1] / ".env"`, and that stays correct — that path becomes the new
repository's root.

### What has to move or change

- `scripts/mcp_smoke_test.py`, which shells into `mcp/.venv/Scripts/python.exe`
  from this repository's root and reads the root `.env`. It is the only
  thing that exercises both sides together, so it has to keep working — from
  the new repository, against a deployment reachable over the network.
- The MCP sections of [README](../README.md),
  [USER-GUIDE](../USER-GUIDE.md) section 4, [[API and MCP]], and
  [[Architecture]]'s repository map.

### The cost to plan for

The API contract becomes cross-repository. Today a change to
`/applications/track`'s shape is one commit touching both sides. Afterwards
a backend change can silently break every deployed client, and users update
on their own schedule, so old clients will be in the field. The lightest
useful mitigations are a minimum-API-version assertion at MCP startup, or a
documented contract with the smoke test as its check. Undecided.

Also note that the server's `instructions` string is load-bearing: it is
what makes an assistant record every job it handles unprompted while never
submitting an application. It has to survive repackaging intact.

Sources: [deployment guide](../DEPLOY.md), [Compose](../docker-compose.yml),
[production overlay](../docker-compose.prod.yml), [MCP
package](../mcp/pyproject.toml), [MCP settings](../mcp/athena_mcp/config.py).
