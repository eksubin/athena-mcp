-- From Supabase's official self-hosting reference. Sets JWT expiry as a
-- database-level setting some internal functions read.
\set jwt_exp `echo "$JWT_EXP"`

ALTER DATABASE postgres SET "app.settings.jwt_exp" TO :'jwt_exp';
