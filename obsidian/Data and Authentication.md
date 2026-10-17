# Data and authentication

[[Home]] · [[Workflows]] · [[API and MCP]]

| Table | Purpose |
| --- | --- |
| profiles | Identity and preferences |
| resumes | Resume metadata |
| profile_facts | Extracted structured resume facts |
| qa_bank | Reusable questions and answers |
| jobs | Shared listings |
| job_scores | User-specific scoring records |
| applications | User/job records and status |
| world_plots | User world locations |
| world_structures | Structures from application progress |
| access_tokens | Hashed personal access tokens |

Resume files use RESUME_STORAGE_DIR and the resumes Docker volume. Postgres persists in db_data.

Web sessions come from GoTrue. The API verifies HS256 JWTs with the shared signing secret and audience authenticated.

MCP uses a personal access token created in Settings. The API resolves its hash through a service-role lookup, then mints a five-minute user JWT for PostgREST. Both web and MCP requests consequently use user-scoped RLS. Only the token hash is stored; the raw token is shown once.

The first authenticated API request lazily creates a profile and world plot, with conflict handling for concurrent initial requests.

RLS scopes personal records to their owner. Signed-in users can read jobs; privileged ingestion uses the service role. World read policies permit public reads at the database layer, while API world endpoints require authentication.

Keep JWT signing secrets and service-role credentials out of public frontend variables. The anon key is the browser-facing key.

Sources: [schema and RLS](../supabase/migrations/0001_init.sql), [auth](../backend/app/core/auth.py), [request dependencies](../backend/app/api/deps.py).
