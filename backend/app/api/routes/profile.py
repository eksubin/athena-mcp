from fastapi import APIRouter, Depends

from app.api.deps import AuthedUser, get_current_user
from app.schemas.profile import ProfileOut, ProfileUpdate
from app.schemas.resume import ProfileFactOut

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
def get_profile(user: AuthedUser = Depends(get_current_user)) -> dict:
    result = user.client.table("profiles").select("*").eq("id", user.user_id).single().execute()
    return result.data


@router.patch("", response_model=ProfileOut)
def update_profile(body: ProfileUpdate, user: AuthedUser = Depends(get_current_user)) -> dict:
    updates = body.model_dump(exclude_none=True)
    result = user.client.table("profiles").update(updates).eq("id", user.user_id).execute()
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
