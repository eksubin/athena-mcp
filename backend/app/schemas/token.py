from datetime import datetime

from pydantic import BaseModel


class TokenCreateIn(BaseModel):
    label: str = "MCP token"


class TokenCreated(BaseModel):
    id: str
    label: str
    token: str  # only ever returned here, at creation time


class TokenOut(BaseModel):
    id: str
    label: str
    created_at: datetime
    last_used_at: datetime | None = None
