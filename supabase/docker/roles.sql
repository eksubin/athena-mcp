-- From Supabase's official self-hosting reference (supabase/supabase,
-- docker/volumes/db/roles.sql). The supabase/postgres image already
-- creates these roles; this just sets their passwords to match
-- POSTGRES_PASSWORD so auth/rest can actually connect as them.
\set pgpass `echo "$POSTGRES_PASSWORD"`

-- supabase_functions_admin isn't created by this image (no Edge Functions
-- support baked in) — confirmed by querying pg_roles rather than assuming
-- parity with the full self-hosting reference, which includes it.
ALTER USER authenticator WITH PASSWORD :'pgpass';
ALTER USER pgbouncer WITH PASSWORD :'pgpass';
ALTER USER supabase_auth_admin WITH PASSWORD :'pgpass';
ALTER USER supabase_storage_admin WITH PASSWORD :'pgpass';
