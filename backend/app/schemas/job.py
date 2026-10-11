from datetime import datetime

from pydantic import BaseModel, Field


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


class JobCreate(BaseModel):
    """One inbound listing. `source` + `external_id` is the upsert key, so
    re-importing the same listing updates it instead of duplicating it."""

    source: str = Field(min_length=1)
    external_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    url: str = Field(min_length=1)
    description: str | None = None
    location: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    remote: bool = False
    easy_apply: bool = False
    posted_at: datetime | None = None
