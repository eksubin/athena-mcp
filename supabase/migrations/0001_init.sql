-- Athena — Phase 0 schema.
-- Matches the data model in the project spec: profiles/resumes/facts/qa_bank
-- are private-by-default; jobs/world_plots/world_structures are readable by
-- any signed-in user but writable only by their owner (or, for jobs, only by
-- the service role used by the ingestion worker).

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- profiles
-- ---------------------------------------------------------------------------
create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  username text not null unique,
  avatar_seed text not null default encode(gen_random_bytes(8), 'hex'),
  real_name text,
  preferences jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "users read own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "users insert own profile"
  on public.profiles for insert
  with check (auth.uid() = id);

create policy "users update own profile"
  on public.profiles for update
  using (auth.uid() = id);

grant select, insert, update on public.profiles to authenticated;

-- Column-level public exposure: only username + avatar, never real_name or
-- preferences. This view is owned by the migration role, so it sees every
-- row regardless of the caller's RLS grant on the base table — the privacy
-- boundary here is the column list, not a row filter.
create view public.public_profiles as
  select id, username, avatar_seed from public.profiles;

grant select on public.public_profiles to authenticated;

-- ---------------------------------------------------------------------------
-- resumes  (row only — the file itself lives on the VPS's local volume)
-- ---------------------------------------------------------------------------
create table public.resumes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  storage_path text not null,
  original_filename text not null,
  uploaded_at timestamptz not null default now(),
  parsed_at timestamptz
);

alter table public.resumes enable row level security;

create policy "users manage own resumes"
  on public.resumes for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

grant select, insert, update, delete on public.resumes to authenticated;

-- ---------------------------------------------------------------------------
-- profile_facts
-- ---------------------------------------------------------------------------
create table public.profile_facts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  key text not null,
  value text not null,
  source_resume_id uuid references public.resumes (id) on delete set null,
  confidence real not null default 1.0 check (confidence >= 0 and confidence <= 1),
  created_at timestamptz not null default now(),
  unique (user_id, key)
);

alter table public.profile_facts enable row level security;

create policy "users manage own profile facts"
  on public.profile_facts for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

grant select, insert, update, delete on public.profile_facts to authenticated;

-- ---------------------------------------------------------------------------
-- qa_bank
-- ---------------------------------------------------------------------------
create table public.qa_bank (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  question text not null,
  answer text not null,
  sensitive boolean not null default false,
  confirmed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (user_id, question)
);

alter table public.qa_bank enable row level security;

create policy "users manage own qa bank"
  on public.qa_bank for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

grant select, insert, update, delete on public.qa_bank to authenticated;

-- ---------------------------------------------------------------------------
-- jobs  (shared catalog, written only by the ingestion worker's service role)
-- ---------------------------------------------------------------------------
create table public.jobs (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  external_id text not null,
  title text not null,
  company text not null,
  url text not null,
  description text,
  location text,
  salary_min integer,
  salary_max integer,
  remote boolean not null default false,
  easy_apply boolean not null default false,
  posted_at timestamptz,
  ingested_at timestamptz not null default now(),
  unique (source, external_id)
);

alter table public.jobs enable row level security;

create policy "jobs are readable by any signed-in user"
  on public.jobs for select
  using (auth.role() = 'authenticated');

-- No insert/update policy for `authenticated`: only the service role (which
-- bypasses RLS) may write here. That's the worker in Phase 3, and the manual
-- seeding/admin path used for local dev until then.
grant select on public.jobs to authenticated;

-- ---------------------------------------------------------------------------
-- job_scores  (per-user — scoring depends on personal preferences)
-- ---------------------------------------------------------------------------
create table public.job_scores (
  job_id uuid not null references public.jobs (id) on delete cascade,
  user_id uuid not null references public.profiles (id) on delete cascade,
  score smallint not null check (score between 0 and 100),
  signals jsonb not null default '{}'::jsonb,
  scored_at timestamptz not null default now(),
  primary key (job_id, user_id)
);

alter table public.job_scores enable row level security;

create policy "users manage own job scores"
  on public.job_scores for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

grant select, insert, update, delete on public.job_scores to authenticated;

create index job_scores_user_score_idx on public.job_scores (user_id, score desc);

-- ---------------------------------------------------------------------------
-- applications
-- ---------------------------------------------------------------------------
create type public.application_status as enum (
  'saved', 'applied', 'pending', 'interview', 'offer', 'rejected'
);

create table public.applications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  job_id uuid not null references public.jobs (id) on delete cascade,
  status public.application_status not null default 'saved',
  notes text,
  applied_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, job_id)
);

alter table public.applications enable row level security;

create policy "users manage own applications"
  on public.applications for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

grant select, insert, update, delete on public.applications to authenticated;

create index applications_user_status_idx on public.applications (user_id, status);

-- ---------------------------------------------------------------------------
-- world_plots  (one per user, frontier-allocated at signup)
-- ---------------------------------------------------------------------------
create table public.world_plots (
  user_id uuid primary key references public.profiles (id) on delete cascade,
  origin_x integer not null,
  origin_y integer not null,
  claimed_at timestamptz not null default now(),
  unique (origin_x, origin_y)
);

alter table public.world_plots enable row level security;

create policy "plots are publicly readable"
  on public.world_plots for select
  using (true);

create policy "users create their own plot"
  on public.world_plots for insert
  with check (auth.uid() = user_id);

grant select, insert on public.world_plots to authenticated;

-- ---------------------------------------------------------------------------
-- world_structures  (one row per application status transition)
-- ---------------------------------------------------------------------------
create type public.structure_type as enum ('sapling', 'tree', 'house', 'landmark', 'stump');

create table public.world_structures (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  application_id uuid references public.applications (id) on delete set null,
  type public.structure_type not null,
  grid_x integer not null,
  grid_y integer not null,
  created_at timestamptz not null default now()
);

alter table public.world_structures enable row level security;

create policy "structures are publicly readable"
  on public.world_structures for select
  using (true);

create policy "users place their own structures"
  on public.world_structures for insert
  with check (auth.uid() = user_id);

grant select, insert on public.world_structures to authenticated;

create index world_structures_user_idx on public.world_structures (user_id);

-- Live "watch others build" relies on Realtime change streams for these two.
alter publication supabase_realtime add table public.world_plots;
alter publication supabase_realtime add table public.world_structures;

-- ---------------------------------------------------------------------------
-- access_tokens  (personal access tokens the MCP server authenticates with)
-- ---------------------------------------------------------------------------
create table public.access_tokens (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  label text not null default 'MCP token',
  token_hash text not null unique,
  created_at timestamptz not null default now(),
  last_used_at timestamptz
);

alter table public.access_tokens enable row level security;

create policy "users manage own tokens"
  on public.access_tokens for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

grant select, insert, update, delete on public.access_tokens to authenticated;

-- Note: resolving a raw bearer token to a user_id happens before the caller
-- is known to be that user, so that one lookup goes through the backend's
-- service-role client (bypassing RLS) — the same bootstrap problem any
-- API-key scheme has. Everything after that lookup uses a JWT minted for
-- that specific user, so RLS applies normally for the rest of the request.
