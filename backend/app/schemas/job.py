from datetime import datetime

from pydantic import BaseModel, Field


class JobSummary(BaseModel):
    id: str
    title: str
    company: str
    # Included in summaries, not just full detail: the link is what an
    # agent (or a person on the dashboard) needs to actually open the
    # listing, and having to fetch each job individually just to get it
    # defeats the point of a compact ranked list.
    url: str
    source: str | None = None
    location: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    remote: bool
    easy_apply: bool
    posted_at: datetime | None = None
    score: int | None = None


class JobDetail(JobSummary):
    external_id: str | None = None
    description: str | None = None
    ingested_at: datetime | None = None


class JobFields(BaseModel):
    """Everything about a listing that a caller can observe and send.

    Shared by bulk import and application tracking so both accept the same
    detail — a browser agent reading a listing page has the description,
    salary and posting date in front of it, and there's no reason for the
    tracking path to drop them.
    """

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


class JobCreate(JobFields):
    """One inbound listing. `source` + `external_id` is the upsert key, so
    re-importing the same listing updates it instead of duplicating it."""

    source: str = Field(min_length=1)
    external_id: str = Field(min_length=1)
