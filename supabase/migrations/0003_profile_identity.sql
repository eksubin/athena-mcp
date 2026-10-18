-- Athena — a profile identity people choose for themselves.
--
-- `username` already existed, assigned at signup and never editable. It is
-- the one thing other people see on the shared map, so it should be the
-- user's own choice; this adds the shape rules that make a chosen handle
-- safe to show, and a small fixed set of avatars to pick from.
--
-- The avatar is a key, not an image: the five drawings live in the web app
-- (frontend/src/components/avatar.tsx) and the database only records which
-- one was chosen. A check constraint keeps that column honest, because it
-- is written by the user's own client through PostgREST.

-- ---------------------------------------------------------------------------
-- username rules
-- ---------------------------------------------------------------------------
-- Lower-case letters, digits and single inner hyphens, 3–24 characters,
-- starting with a letter. Narrow on purpose: this is a public handle, and
-- the shape rules out whitespace, homograph tricks with mixed case, and
-- names that could be read as an email address or a URL fragment.
--
-- Every username generated so far (adjective-noun-NN) already satisfies
-- this, so existing rows need no repair — but validate rather than assume,
-- and fail loudly here instead of leaving a constraint that cannot be
-- added on a real deployment.
do $$
declare
  offenders text;
begin
  select string_agg(username, ', ')
  into offenders
  from public.profiles
  where username !~ '^[a-z][a-z0-9]*(-[a-z0-9]+)*$'
     or length(username) not between 3 and 24;
  if offenders is not null then
    raise exception 'usernames that do not fit the new rules: %', offenders;
  end if;
end;
$$;

alter table public.profiles
  add constraint profiles_username_shape
  check (username ~ '^[a-z][a-z0-9]*(-[a-z0-9]+)*$' and length(username) between 3 and 24);

-- Reserved handles: names that would let an account impersonate the system
-- or sit on a route. Checked here rather than in the API because the
-- profile row is written by the user's own client.
create table public.reserved_usernames (
  username text primary key
);

insert into public.reserved_usernames (username) values
  ('athena'), ('admin'), ('administrator'), ('root'), ('support'), ('help'),
  ('system'), ('staff'), ('team'), ('official'), ('moderator'), ('security'),
  ('settings'), ('profile'), ('dashboard'), ('world'), ('login'), ('logout'),
  ('api'), ('auth'), ('invite'), ('invites'), ('me'), ('you'), ('null'),
  ('undefined'), ('anonymous');

-- No grant to `authenticated`: the guard below reads it as SECURITY
-- DEFINER, and the list is not the client's business.

-- ---------------------------------------------------------------------------
-- avatar
-- ---------------------------------------------------------------------------
alter table public.profiles
  add column avatar text not null default 'fox'
  check (avatar in ('fox', 'owl', 'cat', 'bear', 'fawn'));

-- Existing accounts keep a stable, already-assigned-feeling avatar rather
-- than all turning into foxes: derive each one from the random avatar_seed
-- they were given at signup.
--
-- Spread by a byte of the MD5 rather than by hashtext(): hashtext's low
-- bits are not uniform enough for a modulus this small — on the seeds in
-- this database it handed every account the same avatar.
update public.profiles
set avatar = (array['fox', 'owl', 'cat', 'bear', 'fawn'])[
  1 + (get_byte(decode(md5(avatar_seed), 'hex'), 0) % 5)
];

-- The public view is the only thing other users read, so the chosen avatar
-- belongs in it — still columns-only exposure, never real_name, role or
-- preferences.
create or replace view public.public_profiles as
  select id, username, avatar_seed, avatar from public.profiles;

grant select on public.public_profiles to authenticated;

-- The admin panel lists accounts by who they are, so it shows the same
-- face everybody else sees. `avatar` goes on the end: CREATE OR REPLACE
-- VIEW may only append columns, never insert one into the existing list.
create or replace view public.admin_accounts as
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
    ) as application_count,
    p.avatar
  from public.profiles p
  join auth.users u on u.id = p.id;

grant select on public.admin_accounts to service_role;

-- ---------------------------------------------------------------------------
-- The guard on a renamed profile
-- ---------------------------------------------------------------------------
-- Reserved names and a case-insensitive uniqueness rule. `username` is
-- already unique, but only exactly: without this, "Quiet-Meadow-76" and
-- "quiet-meadow-76" could coexist — the shape constraint forbids upper
-- case anyway, so this guards the gap left if that ever relaxes, and
-- gives a clear failure instead of a raw constraint violation.
--
-- SECURITY DEFINER to read reserved_usernames and other profiles' names,
-- which this caller's RLS hides. `is_privileged_caller()` reads
-- PostgREST's request claims rather than `current_user`, which inside a
-- SECURITY DEFINER function is this function's owner — see
-- 0002_invites_and_admin.sql.
create or replace function public.profiles_guard_username()
returns trigger
language plpgsql
security definer
set search_path = public, pg_catalog
as $$
begin
  if tg_op = 'UPDATE' and new.username = old.username then
    return new;
  end if;
  if exists (select 1 from public.reserved_usernames r where r.username = new.username) then
    raise exception 'athena_username_reserved'
      using errcode = 'check_violation';
  end if;
  if exists (
    select 1 from public.profiles p
    where lower(p.username) = lower(new.username) and p.id <> new.id
  ) then
    raise exception 'athena_username_taken'
      using errcode = 'unique_violation';
  end if;
  return new;
end;
$$;

create trigger profiles_guard_username
  before insert or update of username on public.profiles
  for each row execute function public.profiles_guard_username();
