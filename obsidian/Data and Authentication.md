# Data and authentication

[[Home]] · [[Workflows]] · [[API and MCP]] · [[Invites and Administration]]

| Table | Purpose |
| --- | --- |
| profiles | Identity (username, avatar), preferences, role, suspension, invite allowance |
| resumes | Resume metadata |
| profile_facts | Extracted structured resume facts |
| qa_bank | Reusable questions and answers |
| jobs | Shared listings |
| job_scores | User-specific scoring records |
| applications | User/job records and status |
| world_plots | User world locations |
| world_structures | Structures from application progress |
| access_tokens | Hashed personal access tokens |
| invites | The allowlist of addresses permitted to hold an account |
| reserved_usernames | Handles nobody may take |

Resume files use RESUME_STORAGE_DIR and the resumes Docker volume. Postgres persists in db_data.

Web sessions come from GoTrue. The API verifies HS256 JWTs with the shared signing secret and audience authenticated.

MCP uses a personal access token created in Settings. The API resolves its hash through a service-role lookup, then mints a five-minute user JWT for PostgREST. Both web and MCP requests consequently use user-scoped RLS. Only the token hash is stored; the raw token is shown once.

Registration is closed. A database trigger on `auth.users` refuses an account whose address has no live invite, which covers Google OAuth and the email/password test login alike. Every authenticated request also refuses a suspended profile, because an account that loses access keeps a valid session and valid personal access tokens until they expire. See [[Invites and Administration]].

The first authenticated API request lazily creates a profile and world plot, with conflict handling for concurrent initial requests. That profile's `role` is copied from the invite that admitted it; `role`, `disabled_at` and `invite_limit` are trigger-protected against writes from a client acting as itself, and are changed only by the admin endpoints.

RLS scopes personal records to their owner. Signed-in users can read jobs; privileged ingestion uses the service role. World read policies permit public reads at the database layer, while API world endpoints require authentication.

Keep JWT signing secrets and service-role credentials out of public frontend variables. The anon key is the browser-facing key.

## Chosen identity

A user picks their own `username` and one of five `avatar` keys; the
drawings live in the web app and the database stores only which was
chosen. Both are public — `public_profiles` exposes them, and nothing
else, to other signed-in users.

Usernames are lower-case letters, digits and single inner hyphens, 3–24
characters, starting with a letter, enforced by a check constraint. A
trigger additionally refuses reserved handles and a name another account
holds in different case. The API mirrors the same rules so the refusal
arrives as a sentence rather than a constraint name; the database is the
authority, since the profile row is written with the user's own JWT.

Sources: [schema and RLS](../supabase/migrations/0001_init.sql), [invites and admin](../supabase/migrations/0002_invites_and_admin.sql), [chosen identity](../supabase/migrations/0003_profile_identity.sql), [auth](../backend/app/core/auth.py), [request dependencies](../backend/app/api/deps.py).
