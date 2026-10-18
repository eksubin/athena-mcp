# Going live

[[Home]] · [[Operations]] · [[Local Setup]] · [[Architecture]]

Planning notes for the move off this machine: picking a host, what bites
during the first deploy, and splitting the MCP server into its own
repository. [[Operations]] covers running the stack once it is up; this note
covers the decisions taken before that.

Decisions recorded here were taken on 2026-10-18. The host choice has not
been acted on: nothing is deployed and the repository still has no git
remote. The MCP split below has since been built — see that section.

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

Done, as a prepared state in commit `a240270`: `mcp/` is now a
self-contained repository root. It still sits in this repository, because
the GitHub repository it belongs in does not exist yet — creating it and
moving the tree across is one step, and the last one.

### Why

Athena is invite-only, so every new user was personally invited — but
connecting an assistant used to mean obtaining a copy of this repository,
installing `uv`, running `uv sync`, and putting an absolute path into a
client config. That is a developer-grade install to hand someone who was
just invited.

The whole of a new user's configuration is now:

```json
{"mcpServers": {"athena": {
  "command": "uvx",
  "args": ["--from", "git+https://github.com/<owner>/athena-mcp", "athena-mcp"],
  "env": {"ATHENA_API_URL": "https://api.<domain>",
          "ATHENA_TOKEN": "athena_pat_..."}}}}
```

No checkout, no sync, no paths. Verified against the tree as it stands:
`uvx --from <path-to-mcp> athena-mcp`, launched from a directory with
nothing of Athena in it and configured through environment variables
alone, serves all ten tools. Publishing to a registry stays unnecessary
once the repository is reachable; the name `athena-mcp` is free on PyPI if
that ever changes.

### What moved

- `scripts/mcp_smoke_test.py` → `mcp/scripts/smoke_test.py`. It used to
  shell into `mcp/.venv/Scripts/python.exe` from this repository's root
  and read the root `.env`; it now launches `sys.executable` from a
  temporary directory and takes the deployment from the environment
  (`ATHENA_API_URL`, `ATHENA_SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`,
  `SUPABASE_JWT_SECRET`). It is still the only check that exercises both
  sides together, and it still passes against the local docker stack.
- A README written for someone who has never seen Athena, its own
  `.gitignore`, and `pyjwt` as the one dev dependency the smoke test adds.
- The MCP sections of [README](../README.md),
  [USER-GUIDE](../USER-GUIDE.md) section 4, [[API and MCP]] and
  [[Architecture]]'s repository map now describe a separate installable
  package rather than a folder.

### What the split exposed

`config.py` resolving `parents[1] / ".env"` does stay correct — that path
becomes the new repository's root — but in an *installed* copy it resolves
inside site-packages, where no `.env` will ever be. Harmless, now
commented: environment variables are the real path for installed users,
and they still take precedence over the file for a checkout.

Worse was that `server.py` built `Settings()` and the client at module
import, and `Settings.token` has no default. A config block with a
mistyped `ATHENA_TOKEN` therefore produced a pydantic traceback, which an
MCP client shows as nothing but a server that failed to start — the single
most likely failure for the non-technical invitee this whole change is
for. Both are now built in `main()`, and the two mistakes a new user
actually makes say so in plain English: a missing `ATHENA_TOKEN` names the
variable and the Settings page it comes from, and a token the deployment
rejects is caught by the same startup check.

### The cross-repository contract

The cost was real and is now guarded. `/health` advertises two integers
from `backend/app/core/contract.py` — `mcp_contract`, the contract this
deployment speaks, and `mcp_contract_min`, the oldest client it still
supports. The client declares its own in `athena_mcp/contract.py` and
compares once at startup: below the minimum it refuses to start and gives
the `uvx --refresh` line to update; ahead of the server it warns and
continues, because someone who updated early should still get their work
done; unreachable or unversioned, it starts quietly and lets each tool
report the real error. Both numbers are at 1.

[mcp/CONTRACT.md](../mcp/CONTRACT.md) is the endpoint list the number
covers, the two behaviours that are load-bearing rather than incidental
(`POST /applications` staying idempotent without resetting status, and
`POST /applications/track` ignoring fields the caller omitted), and the
rules for moving either number. `mcp/scripts/smoke_test.py` is its
executable check and asserts the handshake alongside all ten tools: run it
after changing anything on either side.

The server's `instructions` string survived repackaging intact — it is
what makes an assistant record every job it handles unprompted while never
submitting an application, and the smoke test asserts it is still there.

### Left to do

- Create the GitHub repository, move `mcp/` across, delete it here.
- Replace `<owner>` wherever the git URL appears: both READMEs,
  USER-GUIDE section 4, `mcp/CONTRACT.md`, [[API and MCP]], and this note.
- Drop the "prepared state" notes from [README](../README.md)'s status
  bullet and repository map and from [[Architecture]].

Sources: [deployment guide](../DEPLOY.md), [Compose](../docker-compose.yml),
[production overlay](../docker-compose.prod.yml), [MCP
package](../mcp/pyproject.toml), [MCP contract](../mcp/CONTRACT.md).
