"""The admin panel's API.

Everything here runs through the service client rather than the caller's
own JWT, and that is the whole point: these endpoints read other people's
accounts and write the three columns a user is specifically not allowed to
write about themselves (`role`, `disabled_at`, `invite_limit`). RLS cannot
express "unless you are an admin" for this app, because an admin's
authority comes from a profile column, not from the JWT role — so the
authorization check is `get_admin_user`, evaluated before any of this runs.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import AuthedUser, get_admin_user
from app.core.supabase import service_client
from app.schemas.admin import AdminAccount, AdminAccountUpdate, AdminOverview
from app.schemas.invite import AdminInviteCreate, AdminInviteOut

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_admin_user)])


@router.get("/overview", response_model=AdminOverview)
def overview() -> dict:
    accounts = service_client().table("admin_accounts").select("role,disabled_at").execute().data
    pending = (
        service_client()
        .table("admin_invites")
        .select("id", count="exact")
        .is_("revoked_at", "null")
        .is_("accepted_at", "null")
        .execute()
        .count
        or 0
    )
    return {
        "members": sum(1 for a in accounts if a["role"] == "member"),
        "admins": sum(1 for a in accounts if a["role"] == "admin"),
        "disabled": sum(1 for a in accounts if a["disabled_at"]),
        "pending_invites": pending,
    }


@router.get("/users", response_model=list[AdminAccount])
def list_accounts() -> list[dict]:
    return (
        service_client()
        .table("admin_accounts")
        .select("*")
        .order("created_at", desc=False)
        .execute()
        .data
    )


@router.patch("/users/{user_id}", response_model=AdminAccount)
def update_account(
    user_id: str, body: AdminAccountUpdate, admin: AuthedUser = Depends(get_admin_user)
) -> dict:
    """Change someone's role, invite allowance, or whether they still have
    access."""
    updates: dict = {}
    if body.role is not None:
        updates["role"] = body.role
    if body.invite_limit is not None:
        updates["invite_limit"] = body.invite_limit
    if body.disabled is not None:
        updates["disabled_at"] = (
            datetime.now(timezone.utc).isoformat() if body.disabled else None
        )
    if not updates:
        raise HTTPException(422, "Nothing to change")

    # An admin locking themselves out, or demoting the last admin, leaves
    # nobody able to undo it — the panel would simply become unreachable.
    if user_id == admin.user_id and (body.disabled or body.role == "member"):
        raise HTTPException(409, "Ask another administrator to change your own access.")
    if body.role == "member" or body.disabled:
        _require_another_active_admin(user_id)

    result = service_client().table("profiles").update(updates).eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(404, "account not found")
    return _account(user_id)


@router.get("/invites", response_model=list[AdminInviteOut])
def list_all_invites() -> list[dict]:
    return (
        service_client()
        .table("admin_invites")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data
    )


@router.post("/invites", response_model=AdminInviteOut, status_code=201)
def create_invite(
    body: AdminInviteCreate, admin: AuthedUser = Depends(get_admin_user)
) -> dict:
    """Invite an address directly, ignoring invite allowances."""
    live = (
        service_client()
        .table("invites")
        .select("id")
        .eq("email", body.email)
        .is_("revoked_at", "null")
        .execute()
        .data
    )
    if live:
        raise HTTPException(409, "That address already has access, or an invite waiting for it.")
    written = (
        service_client()
        .table("invites")
        .insert(
            {
                "email": body.email,
                "role": body.role,
                "note": body.note,
                "invited_by": admin.user_id,
            }
        )
        .execute()
        .data
    )
    return _invite(written[0]["id"])


@router.delete("/invites/{invite_id}", response_model=AdminInviteOut)
def revoke_invite(invite_id: str, admin: AuthedUser = Depends(get_admin_user)) -> dict:
    """Withdraw an invite — and, if it has already been used, the access it
    granted.

    Revoking the row by itself only closes the door to *new* accounts: the
    database gate runs on signup. So for an invite somebody is already
    using, this suspends that account too, which is what an admin revoking
    access means. Unrevoked, unsuspended, it would be a no-op on the one
    case it most needs to cover.
    """
    existing = (
        service_client()
        .table("invites")
        .select("id,accepted_user_id,revoked_at")
        .eq("id", invite_id)
        .maybe_single()
        .execute()
    )
    # maybe_single().execute() returns None outright when zero rows match.
    if existing is None:
        raise HTTPException(404, "invite not found")
    row = existing.data

    if row["accepted_user_id"]:
        if row["accepted_user_id"] == admin.user_id:
            raise HTTPException(409, "Ask another administrator to withdraw your own access.")
        _require_another_active_admin(row["accepted_user_id"])
        service_client().table("profiles").update(
            {"disabled_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", row["accepted_user_id"]).execute()

    if not row["revoked_at"]:
        service_client().table("invites").update(
            {"revoked_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", invite_id).execute()
    return _invite(invite_id)


def _require_another_active_admin(excluded_user_id: str) -> None:
    """Refuse to remove the last way back into the panel."""
    remaining = (
        service_client()
        .table("admin_accounts")
        .select("id")
        .eq("role", "admin")
        .is_("disabled_at", "null")
        .neq("id", excluded_user_id)
        .execute()
        .data
    )
    if not remaining:
        raise HTTPException(409, "Athena needs at least one active administrator.")


def _account(user_id: str) -> dict:
    return (
        service_client().table("admin_accounts").select("*").eq("id", user_id).single().execute()
    ).data


def _invite(invite_id: str) -> dict:
    return (
        service_client().table("admin_invites").select("*").eq("id", invite_id).single().execute()
    ).data
