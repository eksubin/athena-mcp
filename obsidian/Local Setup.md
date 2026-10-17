# Local setup

[[Home]] · [[API and MCP]] · [[Operations]]

Use Docker and Docker Compose for the full stack. Individual Python services require Python 3.12+ and uv; the frontend requires Node.js and npm.

1. Copy root .env.example to .env.
2. Generate POSTGRES_PASSWORD and JWT_SECRET.
3. Follow the [README](../README.md) JWT script to derive ANON_KEY and SERVICE_ROLE_KEY.
4. Set SUPABASE_ANON_KEY and SUPABASE_SERVICE_ROLE_KEY to the matching keys, and SUPABASE_JWT_SECRET to JWT_SECRET.
5. Set GOOGLE_CLIENT_ID and GOOGLE_SECRET. Register http://localhost:8001/auth/v1/callback as Google's authorized redirect URI.

Start from the project root:

```sh
docker compose up --build
```

After the database is healthy, initialize the application schema. For PowerShell:

```powershell
Get-Content -Raw supabase/migrations/0001_init.sql | docker compose exec -T db psql -U postgres -d postgres -v ON_ERROR_STOP=1
```

Optionally load development sample jobs:

```powershell
Get-Content -Raw supabase/seed.sql | docker compose exec -T db psql -U postgres -d postgres -v ON_ERROR_STOP=1
```

The initial schema is not an idempotent migration runner; do not repeatedly apply it to an initialized database.

Open http://localhost:3000. API health: http://localhost:8000/health. Interactive API reference: http://localhost:8000/docs.

## Individual services

Configure each service from its own environment example. Run these from the corresponding folder:

| Service | Install | Run |
| --- | --- | --- |
| backend | uv sync | uv run uvicorn app.main:app --reload |
| frontend | npm install | npm run dev |
| worker | uv sync | uv run python -m athena_worker.main |
| mcp | uv sync | uv run athena-mcp |

Supabase must still be running. Host processes need host-reachable service URLs rather than Docker service names such as gateway.

Sources: [environment template](../.env.example), [README](../README.md).
