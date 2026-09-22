from datetime import datetime

from pydantic import BaseModel


class ResumeOut(BaseModel):
    id: str
    original_filename: str
    uploaded_at: datetime
    parsed_at: datetime | None = None


class ProfileFactOut(BaseModel):
    key: str
    value: str
    confidence: float
