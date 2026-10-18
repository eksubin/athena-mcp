# Invites and administration

[[Home]] · [[Data and Authentication]] · [[API and MCP]]

Athena is invite-only. An address can hold an account only if a live invite
exists for it, and an account keeps working only while its profile is not
suspended.

## Where the rule is enforced

| Moment | Enforced by |
| --- | --- |
| Creating an account | `before insert` trigger on `auth.users` |
| Claiming the invite | `after insert` trigger on `auth.users` |
| First role assignment | `before insert` trigger on `profiles` |
| Every later request | `get_current_user` refuses a suspended profile (403) |

The signup gate lives on `auth.users` rather than in the API because account
creation happens inside GoTrue — the backend never sees a signup, and Google
OAuth and the email/password test login both insert into that one table.

GoTrue cannot report the reason: a refused signup surfaces as a generic
`Database error saving new user`. The web app translates that into the
invite-only message on the login page.

Revoking an invite closes the door to a *new* account; it does not log out an
account already using it. Withdrawing access from an existing account is a
separate, administrator-only act that sets `profiles.disabled_at`. Admin invite
revocation does both, which is what revoking access means in the panel.

## Privileges a user cannot grant itself

`profiles.role`, `profiles.disabled_at` and `profiles.invite_limit` are written
by triggers, not by clients. A signed-in user can reach PostgREST directly with
their own session JWT, and the `profiles` update policy is row-scoped rather
than column-scoped, so without this a member could simply PATCH itself to
admin. On insert, `role` is copied from the accepted invite; afterwards all
three are writable only by `service_role` — the backend's `/admin` endpoints.

The invite guard trigger applies the same reasoning to `invites`: it enforces
the inviter's allowance, refuses an admin invite from a non-admin, and lets a
member change nothing on an invite except whether it is revoked.

### How a guard knows who is calling

Every guard is `SECURITY DEFINER`, because it has to read rows the caller's
own RLS hides — the invite that admitted them, somebody else's username, the
reserved list. Inside such a function `current_user` is the function's
**owner**, not whoever made the request, so a guard that tests `current_user`
sees `postgres` for a request arriving as `authenticated` and waves it
through. `is_privileged_caller()` therefore reads PostgREST's
`request.jwt.claims`, a session setting that the definer switch does not
touch, and is written to answer "is this caller *known to be* privileged" so
an unrecognized context gets the restrictions rather than a free pass.

`scripts/smoke_test.py` attacks these columns the way they are actually
reachable — straight at PostgREST with a member's own session JWT, with the
API out of the request path entirely.

## Who can invite

Every member can invite, limited by `profiles.invite_limit` (default 3). A live
— not revoked — invite occupies a slot; withdrawing one that has not been used
gives the slot back. Administrators have no limit and can set anyone's
allowance from the panel.

Nothing is emailed. An invite adds the address to the allowlist; the inviter
passes on the link themselves.

## Surfaces

| Surface | Who | What |
| --- | --- | --- |
| /profile → Invite someone in | Any member | Send and withdraw own invites, see the allowance |
| /admin | Administrators | Accounts, roles, allowances, access, all invites |

`/admin` redirects a member to the dashboard, and every `/admin/*` endpoint
refuses one with 403 — the hidden nav link is presentation only.

Admin reads come from `admin_accounts` and `admin_invites`, views granted to
`service_role` alone because they expose email addresses.

## The first administrator

Migration `0002` grandfathers every pre-existing account in as an accepted
invite, then adds a pending **admin** invite for the deployment's first
administrator. Signing in on that address creates an account whose profile is
stamped `admin`, through the same path every later account uses. If the address
already has an account, the migration promotes it instead.

Change the address in that migration before applying it to a new deployment.
Afterwards, roles are managed in the panel.

At least one active administrator always remains: demoting, suspending or
revoking the last one is refused, as is changing your own role or access.

Sources: [migration](../supabase/migrations/0002_invites_and_admin.sql),
[chosen identity](../supabase/migrations/0003_profile_identity.sql),
[invite routes](../backend/app/api/routes/invites.py),
[admin routes](../backend/app/api/routes/admin.py),
[request dependencies](../backend/app/api/deps.py).
