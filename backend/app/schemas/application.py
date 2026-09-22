from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ApplicationStatus = Literal["saved", "applied", "pending", "interview", "offer", "rejected"]


class ApplicationCreate(BaseModel):
    job_id: str


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    note: str | None = None


class ApplicationOut(BaseModel):
    id: str
    job_id: str
    status: ApplicationStatus
    notes: str | None = None
    applied_at: datetime | None = None
    updated_at: datetime
