from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from postgrest.exceptions import APIError

from app.api.deps import AuthedUser, get_current_user
from app.core.supabase import service_client
from app.schemas.invite import InviteCreate, InviteOut

router = APIRouter(prefix="/invites", tags=["invites"])

# The invite guard trigger raises these; mapping them here is what turns a
# PostgREST error into something worth showing a person. The database
# remains the authority — a member can reach PostgREST directly with their
# own session JWT, so these checks cannot live only in the API.
_GUARD_MESSAGES = {
    "athena_invite_limit_reached": (
        409,
        "You've used all of your invites. Ask an administrator for more.",
    ),
    "athena_invite_role_forbidden": (403, "Only an administrator can invite an administrator."),
    "athena_invite_account_disabled": (403, "This account cannot send invites."),
    "athena_invite_unknown_inviter": (403, "Only a signed-in member can send invites."),
    "athena_invite_email_invalid": (422, "Enter a valid email address."),
}


@router.get("", response_model=list[InviteOut])
def list_invites(user: AuthedUser = Depends(get_current_user)) -> list[dict]:
    """Invites this user sent. RLS scopes the read to `invited_by`, so a
    member never sees anyone else's invited addresses."""
    return (
        user.client.table("invites")
        .select("id,email,role,note,created_at,revoked_at,accepted_at,accepted_user_id")
        .eq("invited_by", user.user_id)
        .order("created_at", desc=True)
        .execute()
        .data
    )


@router.post("", response_model=InviteOut, status_code=201)
def create_invite(body: InviteCreate, user: AuthedUser = Depends(get_current_user)) -> dict:
    """Add an address to the allowlist, spending one of this user's
    invites. The address can then create an account; nothing is emailed —
    the inviter passes on the link themselves."""
    _reject_if_already_admitted(body.email)
    try:
        result = (
            user.client.table("invites")
            .insert({"email": body.email, "invited_by": user.user_id, "note": body.note})
            .execute()
        )
    except APIError as exc:
        mapped = _translate(exc)
        if mapped is None:
            raise
        raise mapped from exc
    return result.data[0]


@router.delete("/{invite_id}", status_code=204)
def revoke_invite(invite_id: str, user: AuthedUser = Depends(get_current_user)) -> None:
    """Withdraw an invite that hasn't been used yet, freeing its slot.

    Only pending invites: once someone has an account, taking their access
    away is an administrator's decision, not the inviter's. Revoking the
    row alone would not lock them out anyway — an existing account is
    gated on its own suspension flag, not on the invite.
    """
    existing = (
        user.client.table("invites")
        .select("id,accepted_user_id,revoked_at")
        .eq("id", invite_id)
        .eq("invited_by", user.user_id)
        .maybe_single()
        .execute()
    )
    # maybe_single().execute() returns None outright when zero rows match.
    if existing is None:
        raise HTTPException(404, "invite not found")
    if existing.data["accepted_user_id"]:
        raise HTTPException(
            409,
            "This invite has already been used. An administrator can withdraw that account's access.",
        )
    if existing.data["revoked_at"]:
        return
    user.client.table("invites").update(
        {"revoked_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", invite_id).eq("invited_by", user.user_id).execute()


def _reject_if_already_admitted(email: str) -> None:
    """Explain the partial-unique-index collision before it happens.

    `invites` has one live row per address, and that row may belong to
    somebody else — whose identity this user has no business learning. So
    the message says the address is already covered, never by whom.
    """
    live = (
        service_client()
        .table("invites")
        .select("id,accepted_at")
        .eq("email", email)
        .is_("revoked_at", "null")
        .execute()
        .data
    )
    if live:
        raise HTTPException(
            409,
            "That address already has access to Athena, or an invite waiting for it."
            if live[0]["accepted_at"]
            else "That address already has an invite waiting for it.",
        )


def _translate(exc: APIError) -> HTTPException | None:
    """The guard trigger's refusal as an answer for the caller, or None if
    this isn't one of ours — in which case it's a real fault and the
    original error should surface."""
    for marker, (code, detail) in _GUARD_MESSAGES.items():
        if marker in (exc.message or ""):
            return HTTPException(code, detail)
    if exc.code == "23505":
        return HTTPException(409, "That address already has an invite waiting for it.")
    return None
