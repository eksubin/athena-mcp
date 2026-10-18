-- Athena — invite-only access and admin panel.
--
-- Athena becomes closed-registration: an email can only get an account if
-- somebody already inside invited it. The gate lives on `auth.users`
-- itself rather than in the API, because account creation happens inside
-- GoTrue — the backend never sees a signup, and there are two ways in
-- (Google OAuth and the email/password test login). A trigger on the one
-- table both paths insert into is the only place that covers both.
--
-- Three privileges are deliberately *not* writable by the account they
-- belong to — `profiles.role`, `profiles.disabled_at`,
-- `profiles.invite_limit`. A signed-in user can reach PostgREST directly
-- with their own JWT (the browser has the anon key), and the existing
-- "users update own profile" policy is row-scoped, not column-scoped, so
-- without the guards below a member could simply PATCH themselves to
-- admin. Those three columns are therefore owned by triggers: set from
-- the accepted invite on insert, and thereafter writable only by
-- `service_role` (the backend's admin endpoints).

-- ---------------------------------------------------------------------------
-- profiles — role, suspension, invite allowance
-- ---------------------------------------------------------------------------
alter table public.profiles
  add column role text not null default 'member'
    check (role in ('member', 'admin')),
  add column disabled_at timestamptz,
  -- How many live invites this user may have outstanding. Admins ignore it;
  -- revoking an invite frees its slot again (used = non-revoked invites).
  add column invite_limit smallint not null default 3
    check (invite_limit >= 0);

-- ---------------------------------------------------------------------------
-- invites  (the allowlist; also the audit trail of who let whom in)
-- ---------------------------------------------------------------------------
create table public.invites (
  id uuid primary key default gen_random_uuid(),
  -- Stored lower-cased and trimmed so the signup gate can match on
  -- equality — GoTrue lower-cases the addresses it stores, and an invite
  -- typed as "Someone@Example.com" has to match the account it creates.
  email text not null,
  -- The role the invited account is created with. Only an admin may send
  -- an admin invite (enforced in invites_guard_insert below).
  role text not null default 'member' check (role in ('member', 'admin')),
  invited_by uuid references public.profiles (id) on delete set null,
  note text,
  created_at timestamptz not null default now(),
  revoked_at timestamptz,
  accepted_at timestamptz,
  -- auth.users rather than public.profiles: the invite is accepted the
  -- moment GoTrue creates the account, which is before the backend
  -- lazily creates that user's profile row.
  accepted_user_id uuid references auth.users (id) on delete set null,
  constraint invites_email_lowercase check (email = lower(btrim(email)))
);

-- One live invite per address. A revoked invite stays as history and does
-- not block re-inviting the same person later.
create unique index invites_live_email_idx
  on public.invites (email)
  where revoked_at is null;

create index invites_invited_by_idx on public.invites (invited_by);

alter table public.invites enable row level security;

-- Members see and manage the invites they sent, nothing else: an invite
-- row carries somebody's email address, so it is not public.
create policy "users read own invites"
  on public.invites for select
  using (invited_by = auth.uid());

create policy "users send invites"
  on public.invites for insert
  with check (invited_by = auth.uid());

-- Revoking is an update; which columns an update may actually touch is
-- narrowed by invites_guard_update below.
create policy "users revoke own invites"
  on public.invites for update
  using (invited_by = auth.uid())
  with check (invited_by = auth.uid());

grant select, insert, update on public.invites to authenticated;

-- ---------------------------------------------------------------------------
-- Column-level guards
-- ---------------------------------------------------------------------------

-- Who is actually making this change.
--
-- Read from PostgREST's `request.jwt.claims`, not from `current_user`:
-- every guard below is SECURITY DEFINER (they have to read rows the
-- caller's own RLS hides), and inside a SECURITY DEFINER function
-- `current_user` is the function's owner, not whoever made the request.
-- A guard keyed on `current_user` therefore sees "postgres" for a
-- request arriving as `authenticated` and waves it straight through —
-- which is exactly the escalation these guards exist to stop. The GUC is
-- set per request on the session and is unaffected by that switch.
--
-- Fail-safe by construction: this answers "is this caller *known to be*
-- privileged", so an unrecognized context is treated as a client and gets
-- the restrictions, rather than the other way round.
create or replace function public.is_privileged_caller()
returns boolean
language sql
stable
as $$
  select
    -- Through PostgREST with the service key: the backend's /admin
    -- endpoints. (PGRST_DB_USE_LEGACY_GUCS is false, so the claims
    -- arrive as one JSON document under this name.)
    coalesce(
      nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role',
      ''
    ) = 'service_role'
    -- Or not through PostgREST at all — a migration or psql session,
    -- which connects as a role PostgREST never uses.
    or (
      nullif(current_setting('request.jwt.claims', true), '') is null
      and session_user not in ('authenticator', 'authenticated', 'anon')
    );
$$;

-- `role` is taken from the invite that let this account in, never from the
-- client — the profile row is created by the backend using the *user's*
-- own JWT (see backend/app/api/deps.py), so a client racing it to insert
-- its own profile must not be able to name its own role.
create or replace function public.profiles_apply_invite_grants()
returns trigger
language plpgsql
security definer
set search_path = public, pg_catalog
as $$
begin
  if not public.is_privileged_caller() then
    new.role := coalesce(
      (
        select i.role
        from public.invites i
        where i.accepted_user_id = new.id
          and i.revoked_at is null
        order by i.accepted_at desc nulls last
        limit 1
      ),
      'member'
    );
    new.disabled_at := null;
    new.invite_limit := 3;
  end if;
  return new;
end;
$$;

create trigger profiles_apply_invite_grants
  before insert on public.profiles
  for each row execute function public.profiles_apply_invite_grants();

-- After creation those three columns belong to the admin endpoints alone.
-- Silently restoring the old values (rather than raising) keeps the
-- ordinary PATCH /profile — which only ever sends real_name and
-- preferences — working untouched.
create or replace function public.profiles_guard_privileges()
returns trigger
language plpgsql
security definer
set search_path = public, pg_catalog
as $$
begin
  if not public.is_privileged_caller() then
    new.role := old.role;
    new.disabled_at := old.disabled_at;
    new.invite_limit := old.invite_limit;
  end if;
  return new;
end;
$$;

create trigger profiles_guard_privileges
  before update on public.profiles
  for each row execute function public.profiles_guard_privileges();

-- Quota and role escalation on the way in. The API checks the same quota
-- to return a useful message, but this is the check that actually binds:
-- a member can call PostgREST directly with their session JWT.
create or replace function public.invites_guard_insert()
returns trigger
language plpgsql
security definer
set search_path = public, pg_catalog
as $$
declare
  inviter public.profiles;
  live_invites integer;
begin
  new.email := lower(btrim(new.email));
  if new.email = '' or new.email not like '%_@_%._%' then
    raise exception 'athena_invite_email_invalid'
      using errcode = 'check_violation';
  end if;

  -- The backend's admin endpoints, migrations and psql have already
  -- established who is acting, and may write these rows as given.
  if public.is_privileged_caller() then
    return new;
  end if;


  select * into inviter from public.profiles where id = new.invited_by;
  if not found then
    raise exception 'athena_invite_unknown_inviter'
      using errcode = 'insufficient_privilege';
  end if;
  if inviter.disabled_at is not null then
    raise exception 'athena_invite_account_disabled'
      using errcode = 'insufficient_privilege';
  end if;
  if new.role <> 'member' and inviter.role <> 'admin' then
    raise exception 'athena_invite_role_forbidden'
      using errcode = 'insufficient_privilege';
  end if;

  if inviter.role <> 'admin' then
    select count(*) into live_invites
    from public.invites
    where invited_by = new.invited_by and revoked_at is null;
    if live_invites >= inviter.invite_limit then
      raise exception 'athena_invite_limit_reached'
        using errcode = 'insufficient_privilege';
    end if;
  end if;

  -- Acceptance is recorded by the signup gate, never by the inviter.
  new.accepted_at := null;
  new.accepted_user_id := null;
  new.revoked_at := null;
  return new;
end;
$$;

create trigger invites_guard_insert
  before insert on public.invites
  for each row execute function public.invites_guard_insert();

-- The only thing a member may change on an invite they sent is whether it
-- is revoked. Everything else — who accepted it, when, what role it
-- grants — is history or privilege.
create or replace function public.invites_guard_update()
returns trigger
language plpgsql
security definer
set search_path = public, pg_catalog
as $$
begin
  if not public.is_privileged_caller() then
    new.id := old.id;
    new.email := old.email;
    new.role := old.role;
    new.invited_by := old.invited_by;
    new.created_at := old.created_at;
    new.accepted_at := old.accepted_at;
    new.accepted_user_id := old.accepted_user_id;
  end if;
  return new;
end;
$$;

create trigger invites_guard_update
  before update on public.invites
  for each row execute function public.invites_guard_update();

-- ---------------------------------------------------------------------------
-- The signup gate
-- ---------------------------------------------------------------------------

-- Is this address allowed to hold an account right now? A live (not
-- revoked) invite is the allowlist; an invite that has already been
-- accepted by a *different* account cannot be reused.
create or replace function public.email_may_hold_account(p_email text, p_user_id uuid default null)
returns boolean
language sql
stable
security definer
set search_path = public, pg_catalog
as $$
  select exists (
    select 1
    from public.invites i
    where i.email = lower(btrim(p_email))
      and i.revoked_at is null
      and (
        i.accepted_user_id is null
        or (p_user_id is not null and i.accepted_user_id = p_user_id)
      )
  );
$$;

create or replace function public.auth_users_require_invite()
returns trigger
language plpgsql
security definer
set search_path = public, pg_catalog
as $$
begin
  if new.email is null or btrim(new.email) = '' then
    raise exception 'athena_invite_required'
      using errcode = 'insufficient_privilege',
            hint = 'Athena is invite-only; an email address is required.';
  end if;
  if not public.email_may_hold_account(new.email, new.id) then
    raise exception 'athena_invite_required'
      using errcode = 'insufficient_privilege',
            hint = 'Athena is invite-only. Ask an existing member for an invite.';
  end if;
  return new;
end;
$$;

-- BEFORE: refusing here means GoTrue's insert fails and no account is
-- created, for Google OAuth and the email/password path alike.
create trigger athena_require_invite
  before insert on auth.users
  for each row execute function public.auth_users_require_invite();

-- AFTER: the account row now exists, so the invite's accepted_user_id FK
-- can be satisfied. Separate trigger for exactly that reason.
create or replace function public.auth_users_claim_invite()
returns trigger
language plpgsql
security definer
set search_path = public, pg_catalog
as $$
begin
  update public.invites
  set accepted_at = now(), accepted_user_id = new.id
  where email = lower(btrim(new.email))
    and revoked_at is null
    and accepted_user_id is null;
  return new;
end;
$$;

create trigger athena_claim_invite
  after insert on auth.users
  for each row execute function public.auth_users_claim_invite();

-- ---------------------------------------------------------------------------
-- Admin views  (service_role only — these expose email addresses)
-- ---------------------------------------------------------------------------
-- Not security_invoker, so the view reads through its owner and is not
-- filtered by the caller's RLS; the privacy boundary is the grant below,
-- which deliberately omits `authenticated`.
create view public.admin_accounts as
  select
    p.id,
    p.username,
    p.real_name,
    p.role,
    p.disabled_at,
    p.invite_limit,
    p.created_at,
    u.email,
    u.last_sign_in_at,
    (
      select count(*) from public.invites i
      where i.invited_by = p.id and i.revoked_at is null
    ) as invites_used,
    (
      select count(*) from public.applications a where a.user_id = p.id
    ) as application_count
  from public.profiles p
  join auth.users u on u.id = p.id;

grant select on public.admin_accounts to service_role;

create view public.admin_invites as
  select
    i.id,
    i.email,
    i.role,
    i.note,
    i.created_at,
    i.revoked_at,
    i.accepted_at,
    i.invited_by,
    inviter.username as invited_by_username,
    i.accepted_user_id,
    accepted.username as accepted_username
  from public.invites i
  left join public.profiles inviter on inviter.id = i.invited_by
  left join public.profiles accepted on accepted.id = i.accepted_user_id;

grant select on public.admin_invites to service_role;

-- ---------------------------------------------------------------------------
-- Bootstrap
-- ---------------------------------------------------------------------------
-- Accounts that already exist predate the gate. Grandfather them in as
-- accepted invites so they keep their access; without this, the first
-- admin action that touches their invite row would find nothing, and a
-- re-created account would be refused.
insert into public.invites (email, role, invited_by, note, created_at, accepted_at, accepted_user_id)
select lower(btrim(u.email)), 'member', null, 'Account predates invite-only access', u.created_at, u.created_at, u.id
from auth.users u
where u.email is not null and btrim(u.email) <> ''
on conflict do nothing;

-- The first admin. A pending admin invite rather than a direct promotion,
-- because the gate and the role assignment then run through exactly the
-- same path every later account uses — signing in with this address
-- creates an account whose profile is stamped 'admin'. If the address
-- already has a (grandfathered) account, promote that account instead.
-- To use a different address, change it in both statements before
-- applying this migration; afterwards, use the admin panel.
insert into public.invites (email, role, note)
select 'edusubin@gmail.com', 'admin', 'Initial administrator'
where not exists (
  select 1 from auth.users u where lower(btrim(u.email)) = 'edusubin@gmail.com'
);

update public.profiles p
set role = 'admin'
from auth.users u
where u.id = p.id and lower(btrim(u.email)) = 'edusubin@gmail.com';

update public.invites
set role = 'admin'
where email = 'edusubin@gmail.com';
