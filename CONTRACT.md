# The API contract

This repository and the Athena backend ship separately. The backend is
deployed once by whoever runs the instance; `athena-mcp` is installed on
each user's own machine and updates whenever that person happens to
update it. So at any moment the deployment is talking to clients of
several different ages, and a backend change that looks harmless can
quietly take ten tools away from someone who isn't in the room.

Two things keep that honest: a version handshake, so a mismatch is
announced instead of discovered, and the list below, so you know what
counts as a change.

## The handshake

`GET /health` advertises two integers:

```json
{ "status": "ok", "mcp_contract": 1, "mcp_contract_min": 1 }
```

- `mcp_contract` — the contract the deployment speaks now.
- `mcp_contract_min` — the oldest client contract it still supports.

This client declares its own in `athena_mcp/contract.py`
(`CONTRACT_VERSION`). At startup it fetches `/health` once and compares:

| Situation | What the user sees |
| --- | --- |
| client within `[min, current]` | nothing; the server starts |
| client below `mcp_contract_min` | the server refuses to start, with the `uvx --refresh` line to update it |
| client above `mcp_contract` | a warning on stderr; the server starts anyway, since most tools still work |
| `/health` unreachable | a warning; the server starts, and each tool reports the real error |
| `/health` advertises no contract | nothing — a deployment older than the handshake, or not Athena |

The same startup check also catches a rejected token, which is the other
thing a new user gets wrong.

## What the number covers

`athena-mcp` is a thin typed client; these are the only endpoints it
touches, and the shapes it depends on:

| Endpoint | Used by | Depends on |
| --- | --- | --- |
| `GET /health` | startup handshake | `mcp_contract`, `mcp_contract_min` |
| `GET /jobs?limit=` | `search_jobs` | a list of jobs, each with `id` and `url` |
| `GET /jobs/{id}` | `get_job`, `start_application` | the full job record |
| `POST /applications/track` | `track_job`, `import_linkedin_job` | accepts a partial listing; returns `job`, `application`, `created`, `status_changed`; omitted fields leave stored values alone |
| `POST /applications` | `save_job`, `start_application`, `update_status` | idempotent on (user, job) — returns the existing record rather than a 409, and does not reset its status |
| `GET /applications?status=` | `get_queue` | each row carries its `job`, including `job.url` |
| `PATCH /applications/{id}` | `update_status` | accepts `status` and `note` |
| `GET /answers` | `start_application` | the answer bank |
| `POST /answers` | `record_answer` | accepts `question`, `answer`, `sensitive` |
| `GET /profile` + `GET /profile/facts` | `get_profile`, `start_application` | facts carry `key`, `value`, `confidence` |

Authentication is a personal access token from the web app's Settings
page, sent as `Authorization: Bearer <token>`.

Two behaviours in that table are load-bearing rather than incidental, and
breaking either one would be invisible until a user lost data:

- `POST /applications` must stay idempotent and must not reset status.
  `save_job`, `start_application` and `update_status` all call it on jobs
  that may already be in the queue.
- `POST /applications/track` must ignore fields the caller omitted. The
  client deliberately sends only what the assistant actually read off the
  page, so a missing `description` must not blank out a stored one.

## Changing either side

**Backend.** Bump `MCP_CONTRACT_VERSION` in `backend/app/core/contract.py`
whenever a row above changes in a way a client could notice: a renamed or
removed response field, a new required request field, a different status
code, a moved route. Additions nothing here reads don't count. Raise
`MCP_CONTRACT_MIN` only when you deliberately drop older clients — that
breaks everyone below it, so do it with a release note telling people to
update, never as a side effect of a refactor.

**This client.** Raise `CONTRACT_VERSION` when it starts relying on an API
change, together with the backend bump that introduced it.

**Either.** `scripts/smoke_test.py` is the check. It runs this client and
a real deployment together over stdio — the only thing that does — and
asserts the handshake alongside all ten tools:

```sh
uv run python scripts/smoke_test.py
```

Run it against the deployment before and after a change on either side.
A change that passes the ten tools but moves the contract number still
needs the number moved; a change that passes nothing needs fixing.
