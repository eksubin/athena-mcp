from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.job import JobFields, JobSummary

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
    # The listing this application is for, read in the same round trip.
    # Without it every consumer — the dashboard, the MCP queue — has to
    # follow up with one GET /jobs/{id} per application just to show a
    # title and a link.
    job: JobSummary | None = None


class ApplicationTrack(JobFields):
    """Record a listing and the user's position on it in one call.

    This is the path an agent working in a browser uses: it has a URL and
    what it read off the page, and no reason to know whether Athena has
    seen this listing before. The catalog key is derived from the URL
    (see app/services/jobs.identify_listing) unless the caller knows it.
    """

    status: ApplicationStatus = "saved"
    note: str | None = None
    source: str | None = Field(default=None, min_length=1)
    external_id: str | None = Field(default=None, min_length=1)


class ApplicationTracked(BaseModel):
    job: JobSummary
    application: ApplicationOut
    # Whether this call created the application rather than finding it, and
    # whether it moved its status — so a caller can tell "already tracked,
    # nothing to do" from real progress without diffing anything.
    created: bool
    status_changed: bool
