# API and MCP

[[Home]] · [[Data and Authentication]] · [[Local Setup]] · [[Invites and Administration]]

Except for /health, these route groups require authentication. Use the running API's /docs for request and response schemas.

| Methods | Path | Purpose |
| --- | --- | --- |
| GET | /health | Basic process health, plus the MCP contract numbers |
| GET, PATCH | /profile | Profile/preferences |
| GET | /profile/facts | Extracted facts |
| GET, POST | /resumes | List/upload resumes |
| GET | /resumes/{resume_id}/facts | Resume facts |
| GET, POST | /answers | List/search and upsert answers |
| GET, POST | /jobs | Ranked search and import |
| GET | /jobs/{job_id} | Full listing |
| GET, POST | /applications | List/filter and save |
| POST | /applications/track | Record a listing and its status in one call |
| PATCH | /applications/{application_id} | Status updates |
| GET | /world/plots, /world/structures | World data |
| GET, POST | /tokens | List/create tokens |
| DELETE | /tokens/{token_id} | Revoke token |
| GET, POST | /invites | Own invites; send one |
| DELETE | /invites/{invite_id} | Withdraw an unused own invite |
| GET | /admin/overview, /admin/users, /admin/invites | Administrator reads |
| PATCH | /admin/users/{user_id} | Role, access, invite allowance |
| POST, DELETE | /admin/invites[/{invite_id}] | Invite directly; withdraw any invite |

Applications come back with their listing embedded, so nothing needs a second request per job to show a title or a link. `/admin` endpoints refuse a non-administrator with 403.

## MCP tools

| Tool | Purpose |
| --- | --- |
| track_job | Record any listing and its status in one call |
| import_linkedin_job | Same, behind a stricter LinkedIn URL check |
| search_jobs | Ranked summaries, with links; default limit 10 |
| get_job | Full selected listing |
| save_job | Save without applying |
| get_queue | Applications, optionally by status |
| start_application | Job, application record, answer bank |
| record_answer | Reusable answer with sensitive flag |
| update_status | Status change and world growth |
| get_profile | Condensed structured facts |

The stdio server delegates to the backend. Search returns compact summaries; fetch full descriptions when needed. Sensitive answers are marked for confirmation in the supervised application flow.

The server's instructions tell an agent to call `track_job` for every listing it handles, unprompted, with the status that is true at that moment — recording is bookkeeping, not an action taken on the user's behalf. `track_job` accepts the whole listing (link, title, company, location, salary range, remote and easy-apply flags, posting date, description, note) and derives the catalog key from the URL, so the same job seen through a search page, a tracking link or a bare URL stays one record. Repeat calls update rather than duplicate, and omitted fields keep whatever Athena already holds. The rule that `applied` requires visible employer confirmation is unchanged.

## Installing it

The MCP server is not part of this stack. It is a separate package, `athena-mcp`, in its own repository, and it runs on the machine the assistant runs on — one per user, updated whenever that user updates it. There is no checkout, no `uv sync` and no absolute path in the configuration: `uvx` fetches and runs it on demand, and the only two settings travel in the client config's `env` block.

```json
{
  "mcpServers": {
    "athena": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/eksubin/Athena", "athena-mcp"],
      "env": {
        "ATHENA_API_URL": "https://api.athena.example.com",
        "ATHENA_TOKEN": "athena_pat_..."
      }
    }
  }
}
```

Create the token at /settings. A checkout of that repository can still use a root `.env` instead; environment variables win over it.

## The cross-repo contract

Because the two ship separately, a backend change can take tools away from a client nobody is watching. `/health` therefore advertises `mcp_contract` (the contract this deployment speaks) and `mcp_contract_min` (the oldest client it still supports), from [[Architecture|backend/app/core/contract.py]]. The client fetches it once at startup: below the minimum it refuses to start and tells the user to update; above the current it warns and continues; unreachable or unversioned, it starts quietly. The same startup check catches a rejected token.

Bump `MCP_CONTRACT_VERSION` when an endpoint the MCP calls changes in a way a client could notice. Raise `MCP_CONTRACT_MIN` only to drop old clients deliberately. The list of what counts, and the integration check that exercises both sides together, live in that repository (`CONTRACT.md` and `scripts/smoke_test.py`).

Sources: [routes](../backend/app/api/routes/), [contract](../backend/app/core/contract.py), [MCP tools](../mcp/athena_mcp/server.py), [MCP contract](../mcp/CONTRACT.md).
