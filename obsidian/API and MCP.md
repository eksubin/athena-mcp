# API and MCP

[[Home]] · [[Data and Authentication]] · [[Local Setup]]

Except for /health, these route groups require authentication. Use the running API's /docs for request and response schemas.

| Methods | Path | Purpose |
| --- | --- | --- |
| GET | /health | Basic process health |
| GET, PATCH | /profile | Profile/preferences |
| GET | /profile/facts | Extracted facts |
| GET, POST | /resumes | List/upload resumes |
| GET | /resumes/{resume_id}/facts | Resume facts |
| GET, POST | /answers | List/search and upsert answers |
| GET, POST | /jobs | Ranked search and import |
| GET | /jobs/{job_id} | Full listing |
| GET, POST | /applications | List/filter and save |
| PATCH | /applications/{application_id} | Status updates |
| GET | /world/plots, /world/structures | World data |
| GET, POST | /tokens | List/create tokens |
| DELETE | /tokens/{token_id} | Revoke token |

## MCP tools

| Tool | Purpose |
| --- | --- |
| search_jobs | Ranked summaries; default limit 10 |
| get_job | Full selected listing |
| save_job | Save without applying |
| get_queue | Applications, optionally by status |
| start_application | Job, application record, answer bank |
| record_answer | Reusable answer with sensitive flag |
| update_status | Status change and world growth |
| get_profile | Condensed structured facts |

The stdio server delegates to the backend. Search returns compact summaries; fetch full descriptions when needed. Sensitive answers are marked for confirmation in the supervised application flow.

Create a token at /settings, configure mcp/.env from its example with ATHENA_API_URL and the token, and run uv sync in mcp.

Example client configuration; replace the directory with this checkout's absolute mcp path:

```json
{
  "mcpServers": {
    "athena": {
      "command": "uv",
      "args": ["--directory", "C:/path/to/Athena/mcp", "run", "athena-mcp"]
    }
  }
}
```

Sources: [routes](../backend/app/api/routes/), [MCP tools](../mcp/athena_mcp/server.py), [MCP environment](../mcp/.env.example).
