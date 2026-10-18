import sys
from typing import Literal

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import ValidationError

from athena_mcp import contract
from athena_mcp.client import AthenaClient
from athena_mcp.config import Settings

_client: AthenaClient | None = None


def client() -> AthenaClient:
    """The API client, built on first use.

    Importing this module must not require a token: a user whose config
    is wrong should get the explanation main() prints, not a pydantic
    traceback from an import they never made themselves.
    """
    global _client
    if _client is None:
        _client = AthenaClient(Settings())
    return _client


mcp = MCPServer("athena", instructions=(
    "Athena is the user's job-search record. Keep it current without being asked: "
    "whenever you look at, discuss, prepare or submit a specific job on the user's behalf, "
    "call track_job for it in the same turn, with the status that is actually true now "
    "(saved while considering, applied once submitted, interview once one is scheduled, and so on). "
    "Do not wait to be told to save or log a job, and do not ask permission to record one - "
    "recording is bookkeeping, not an action taken on the user's behalf. "
    "Pass everything you have actually read from the listing: the link, title, company, "
    "location, salary range, remote and easy-apply flags, posting date and description. "
    "Repeat calls are safe: track_job updates the existing record instead of duplicating it. "
    "Athena stores job-search data; it does not submit employer applications. "
    "Use BrowserOS for LinkedIn and employer forms. start_application prepares context only. "
    "Respect review-only requests: leave the application saved, never mark it applied. "
    "Record applied only after an authorized submission and visible employer confirmation. "
    "Use verified profile facts; ask about missing or low-confidence facts. Confirm sensitive answers before reuse. "
    "Never invent qualifications or bypass sign-in challenges."
))
ApplicationStatus = Literal["saved", "applied", "pending", "interview", "offer", "rejected"]


@mcp.tool()
def search_jobs(limit: int = 10) -> list[dict]:
    """Ranked, pre-scored jobs from Athena: id, title, company, score, url,
    location, salary, easy_apply. Full descriptions are NOT included — call
    get_job for one specific listing only when you actually need it."""
    return client().search_jobs(limit=limit)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def get_job(job_id: str) -> dict:
    """Full detail for one job: description, URL, posted date."""
    return client().get_job(job_id)


@mcp.tool()
def track_job(
    url: str,
    title: str,
    company: str,
    status: ApplicationStatus = "saved",
    location: str | None = None,
    description: str | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    remote: bool | None = None,
    easy_apply: bool | None = None,
    posted_at: str | None = None,
    note: str | None = None,
) -> dict:
    """Record a job in Athena and where the user stands on it. Call this for
    every listing you handle, as soon as you handle it, without being asked.

    One call registers both the listing and the user's application record,
    so there is nothing to look up first and nothing to create in advance.
    Calling it again for the same link updates that record rather than
    adding a second one - so re-track a job whenever its status changes or
    you learn more about it.

    Fill in every field you actually read from the listing; leave out what
    you did not see rather than guessing, and never overwrite an observed
    value with an invented one. Omitted fields keep whatever Athena already
    holds. `posted_at` is an ISO-8601 date or timestamp.

    `status` must be what is true now: saved (considering it), applied
    (submitted, with the employer's confirmation seen), pending, interview,
    offer, rejected. This records the status only - it applies to nothing.

    Returns the stored job (with its Athena id), the application record,
    and whether this call created it or moved its status.
    """
    return client().track_job(
        url, title, company, status=status, location=location, description=description,
        salary_min=salary_min, salary_max=salary_max, remote=remote,
        easy_apply=easy_apply, posted_at=posted_at, note=note,
    )


@mcp.tool()
def import_linkedin_job(
    url: str,
    title: str,
    company: str,
    location: str | None = None,
    description: str | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    remote: bool | None = None,
    easy_apply: bool | None = None,
    posted_at: str | None = None,
) -> dict:
    """Register a LinkedIn listing already inspected in BrowserOS, and save
    it. Prefer track_job unless you specifically want the LinkedIn URL
    check - this accepts only a https://www.linkedin.com/jobs/view/<id>
    link, and rejects a search page URL.

    Copy the listing's actual fields; do not invent any. No LinkedIn fetch,
    save, message or submission happens here."""
    return client().import_linkedin_job(
        url, title, company, location, description=description, salary_min=salary_min,
        salary_max=salary_max, remote=remote, easy_apply=easy_apply, posted_at=posted_at,
    )


@mcp.tool()
def save_job(job_id: str) -> dict:
    """Mark a job as saved, without applying yet."""
    return client().save_job(job_id)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def get_queue(status: ApplicationStatus | None = None) -> list[dict]:
    """Applications, optionally filtered by status: saved, applied, pending,
    interview, offer, or rejected. Each one carries its listing - title,
    company, link, location, salary - so reporting on the queue needs no
    separate job lookups."""
    return client().get_queue(status=status)


@mcp.tool()
def start_application(job_id: str) -> dict:
    """Prepare only; never submits to LinkedIn or an employer. Returns the job, profile facts, the
    (possibly newly-created) application record, and the full Q&A answer
    bank — so the browser-driven form-fill step doesn't have to ask the
    user questions Athena already knows the answer to."""
    return client().start_application(job_id)


@mcp.tool()
def record_answer(question: str, answer: str, sensitive: bool = False) -> dict:
    """Save a reusable answer to the Q&A bank. Mark salary/visa/etc as
    sensitive=True — the plugin still confirms those with the user each
    time rather than reusing them silently."""
    return client().record_answer(question, answer, sensitive)


@mcp.tool()
def update_status(job_id: str, status: ApplicationStatus, note: str | None = None) -> dict:
    """Move an application to a new status: saved, applied, pending,
    interview, offer, or rejected - by Athena job id, for a job already in
    the queue. For a job you have in front of you as a link, track_job does
    this in one call instead.

    Also grows the user's plot in the shared world. This records status
    only. Use applied only after visible employer confirmation of an
    authorized submission; review-only stays saved."""
    return client().update_status(job_id, status, note)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def get_profile() -> dict:
    """Condensed structured profile facts — not the raw CV text."""
    return client().get_profile()


NO_TOKEN = """athena-mcp: ATHENA_TOKEN is not set.

Athena is invite-only. Sign in to the web app, go to Settings -> Personal
access tokens, create one, and give it to your MCP client under exactly
that name:

  "env": {"ATHENA_API_URL": "https://api.example.com", "ATHENA_TOKEN": "athena_pat_..."}

See the README for the full config block."""


def _preflight(api: AthenaClient, api_url: str) -> None:
    """Check, before any tool is offered, the two things a new user gets
    wrong: a token the server rejects, and a client too old for the
    deployment it points at.

    An unreachable server is not one of them — it may just be starting,
    or the laptop may be off the network — so that is a warning and the
    tools report it per call.
    """
    try:
        health = api.health()
    except httpx.HTTPError as error:
        print(f"athena-mcp: cannot reach {api_url} ({error}); starting anyway.", file=sys.stderr)
        return

    refusal = contract.refusal(health, api_url)
    if refusal:
        sys.exit(refusal)
    warning = contract.warning(health)
    if warning:
        print(f"athena-mcp: {warning}", file=sys.stderr)

    try:
        api.get_profile()
    except httpx.HTTPStatusError as error:
        if error.response.status_code in (401, 403):
            sys.exit(
                f"athena-mcp: {api_url} rejected this token.\n\n"
                "It may have been revoked, or belong to another deployment, or the "
                "account's access may have been withdrawn. Create a new one in the "
                "web app under Settings and put it in ATHENA_TOKEN."
            )
        raise
    except httpx.HTTPError as error:
        print(f"athena-mcp: could not read the profile ({error}); starting anyway.", file=sys.stderr)


def main() -> None:
    global _client
    try:
        settings = Settings()
    except ValidationError:
        sys.exit(NO_TOKEN)
    _client = AthenaClient(settings)
    _preflight(_client, settings.api_url)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
