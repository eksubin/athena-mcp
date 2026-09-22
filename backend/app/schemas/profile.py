from pydantic import BaseModel


class ProfileOut(BaseModel):
    id: str
    username: str
    avatar_seed: str
    real_name: str | None = None
    preferences: dict = {}


class ProfileUpdate(BaseModel):
    real_name: str | None = None
    preferences: dict | None = None
