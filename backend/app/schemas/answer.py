from datetime import datetime

from pydantic import BaseModel


class AnswerIn(BaseModel):
    question: str
    answer: str
    sensitive: bool = False


class AnswerOut(AnswerIn):
    id: str
    confirmed_at: datetime | None = None
