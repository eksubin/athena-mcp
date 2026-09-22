from fastapi import APIRouter, Depends

from app.api.deps import AuthedUser, get_current_user
from app.core.auth import generate_personal_access_token
from app.schemas.token import TokenCreated, TokenCreateIn, TokenOut

router = APIRouter(prefix="/tokens", tags=["tokens"])


@router.get("", response_model=list[TokenOut])
def list_tokens(user: AuthedUser = Depends(get_current_user)) -> list[dict]:
    return (
        user.client.table("access_tokens")
        .select("id,label,created_at,last_used_at")
        .eq("user_id", user.user_id)
        .execute()
        .data
    )


@router.post("", response_model=TokenCreated)
def create_token(body: TokenCreateIn, user: AuthedUser = Depends(get_current_user)) -> dict:
    """The raw token is only ever returned here — store it now, it can't be
    retrieved again, only revoked and replaced."""
    raw, token_hash = generate_personal_access_token()
    result = (
        user.client.table("access_tokens")
        .insert({"user_id": user.user_id, "label": body.label, "token_hash": token_hash})
        .execute()
    )
    row = result.data[0]
    return {"id": row["id"], "label": row["label"], "token": raw}


@router.delete("/{token_id}", status_code=204)
def revoke_token(token_id: str, user: AuthedUser = Depends(get_current_user)) -> None:
    user.client.table("access_tokens").delete().eq("id", token_id).eq(
        "user_id", user.user_id
    ).execute()
