from fastapi import APIRouter, Depends

from app.api.deps import AuthedUser, get_current_user
from app.schemas.answer import AnswerIn, AnswerOut

router = APIRouter(prefix="/answers", tags=["answers"])


@router.get("", response_model=list[AnswerOut])
def list_answers(q: str | None = None, user: AuthedUser = Depends(get_current_user)) -> list[dict]:
    query = user.client.table("qa_bank").select("*").eq("user_id", user.user_id)
    if q:
        query = query.ilike("question", f"%{q}%")
    return query.execute().data


@router.post("", response_model=AnswerOut)
def upsert_answer(body: AnswerIn, user: AuthedUser = Depends(get_current_user)) -> dict:
    result = (
        user.client.table("qa_bank")
        .upsert({"user_id": user.user_id, **body.model_dump()}, on_conflict="user_id,question")
        .execute()
    )
    return result.data[0]
