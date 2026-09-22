from datetime import datetime

from pydantic import BaseModel


class JobSummary(BaseModel):
    id: str
    title: str
    company: str
    location: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    remote: bool
    easy_apply: bool
    score: int | None = None


class JobDetail(JobSummary):
    url: str
    description: str | None = None
    posted_at: datetime | None = None
