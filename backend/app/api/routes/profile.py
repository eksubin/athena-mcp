from fastapi import APIRouter, Depends, HTTPException
from postgrest.exceptions import APIError

from app.api.deps import AuthedUser, get_current_user
from app.schemas.profile import ProfileOut, ProfileUpdate
from app.schemas.resume import ProfileFactOut

router = APIRouter(prefix="/profile", tags=["profile"])

# Raised by the username guard trigger, which is the authority here — the
# profile row is written with the user's own JWT, so a client can reach
# PostgREST directly and the API's own validation is only for the message.
_USERNAME_ERRORS = {
    "athena_username_taken": "That name is already taken. Try another.",
    "athena_username_reserved": "That name is reserved. Try another.",
    "profiles_username_shape": (
        "Use lowercase letters, numbers and hyphens, starting with a letter."
    ),
}


@router.get("", response_model=ProfileOut)
def get_profile(user: AuthedUser = Depends(get_current_user)) -> dict:
    result = user.client.table("profiles").select("*").eq("id", user.user_id).single().execute()
    return result.data


@router.patch("", response_model=ProfileOut)
def update_profile(body: ProfileUpdate, user: AuthedUser = Depends(get_current_user)) -> dict:
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(422, "Nothing to change")
    try:
        result = (
            user.client.table("profiles").update(updates).eq("id", user.user_id).execute()
        )
    except APIError as exc:
        mapped = _translate(exc)
        if mapped is None:
            raise
        raise mapped from exc
    return result.data[0]


@router.get("/facts", response_model=list[ProfileFactOut])
def get_profile_facts(user: AuthedUser = Depends(get_current_user)) -> list[dict]:
    """Current best-known facts — one row per key, latest resume upload
    wins (profile_facts is unique on (user_id, key))."""
    return (
        user.client.table("profile_facts")
        .select("key,value,confidence")
        .eq("user_id", user.user_id)
        .execute()
        .data
    )


def _translate(exc: APIError) -> HTTPException | None:
    """The database's refusal as an answer for the caller, or None if this
    isn't one of ours — in which case it's a real fault and the original
    error should surface."""
    haystack = " ".join(filter(None, (exc.message, exc.details, exc.hint)))
    for marker, detail in _USERNAME_ERRORS.items():
        if marker in haystack:
            return HTTPException(409, detail)
    # The plain unique index on `username`, if the guard trigger's
    # case-insensitive check is somehow bypassed.
    if exc.code == "23505":
        return HTTPException(409, _USERNAME_ERRORS["athena_username_taken"])
    return None
