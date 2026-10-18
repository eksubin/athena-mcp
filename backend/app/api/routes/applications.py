from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from postgrest.exceptions import APIError

from app.api.deps import AuthedUser, get_current_user
from app.schemas.application import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationStatusUpdate,
    ApplicationTrack,
    ApplicationTracked,
)
from app.services.jobs import UnusableJobUrl, identify_listing, upsert_jobs
from app.services.world import structure_position, structure_type_for_status

router = APIRouter(prefix="/applications", tags=["applications"])

# PostgREST resource embedding: one request returns each application with
# its listing. Columns are named explicitly to leave `description` out —
# it is the one large field, and nothing listing a queue needs it.
_WITH_JOB = (
    "*,job:jobs(id,title,company,url,source,location,"
    "salary_min,salary_max,remote,easy_apply,posted_at)"
)


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    status: str | None = None, user: AuthedUser = Depends(get_current_user)
) -> list[dict]:
    query = user.client.table("applications").select(_WITH_JOB).eq("user_id", user.user_id)
    if status:
        query = query.eq("status", status)
    return query.order("updated_at", desc=True).execute().data


@router.post("", response_model=ApplicationOut)
def create_application(
    body: ApplicationCreate, user: AuthedUser = Depends(get_current_user)
) -> dict:
    application, created = _upsert_application(user, body.job_id, "saved")
    if created:
        _place_structure(user, application, "saved")
    return _with_job(user, application)


@router.post("/track", response_model=ApplicationTracked)
def track_application(
    body: ApplicationTrack, user: AuthedUser = Depends(get_current_user)
) -> dict:
    """Register a listing and the user's position on it in one call.

    Deliberately idempotent in both halves: the listing upserts on its
    catalog key and the application upserts on (user, job). Calling this
    again for a job already being tracked reports the existing record
    instead of failing, so an agent can record every listing it handles
    without first checking whether Athena already knows it.
    """
    try:
        source, external_id = (
            (body.source, body.external_id)
            if body.source and body.external_id
            else identify_listing(body.url)
        )
    except UnusableJobUrl as exc:
        raise HTTPException(422, str(exc)) from exc

    fields = body.model_dump(
        mode="json",
        exclude_unset=True,
        exclude={"status", "note", "source", "external_id"},
    )
    written = upsert_jobs([{**fields, "source": source, "external_id": external_id}])
    if not written:
        raise HTTPException(500, "could not record this listing")
    job = written[0]

    application, created = _upsert_application(user, job["id"], body.status)
    status_changed = created or application["status"] != body.status

    if created:
        if body.note is not None:
            application = _write_note(user, application["id"], body.note)
    elif status_changed:
        application = _apply_status(user, application["id"], body.status, body.note)
    elif body.note is not None:
        application = _write_note(user, application["id"], body.note)

    # Same rule as PATCH: a status the user has actually reached grows the
    # world. Re-tracking a job at its current status grows nothing, or the
    # plot would fill up with every repeat call.
    if status_changed:
        _place_structure(user, application, body.status)

    return {
        "job": job,
        # Filled in from the listing already in hand rather than re-read:
        # an application record whose embedded `job` were null next to a
        # populated sibling would read as "this job is unknown".
        "application": {**application, "job": job},
        "created": created,
        "status_changed": status_changed,
    }


@router.patch("/{application_id}", response_model=ApplicationOut)
def update_status(
    application_id: str,
    body: ApplicationStatusUpdate,
    user: AuthedUser = Depends(get_current_user),
) -> dict:
    application = _apply_status(user, application_id, body.status, body.note)
    _place_structure(user, application, body.status)
    return _with_job(user, application)


def _upsert_application(
    user: AuthedUser, job_id: str, status: str
) -> tuple[dict, bool]:
    """Return (application, created). `applications` is unique on
    (user_id, job_id), so saving an already-saved job is a no-op that
    returns the existing record rather than a 409 the caller has to
    special-case."""
    existing = (
        user.client.table("applications")
        .select("*")
        .eq("user_id", user.user_id)
        .eq("job_id", job_id)
        .maybe_single()
        .execute()
    )
    # maybe_single().execute() returns None outright (not a response with
    # .data = None) when zero rows match.
    if existing is not None:
        return existing.data, False

    row: dict = {"user_id": user.user_id, "job_id": job_id, "status": status}
    if status == "applied":
        row["applied_at"] = datetime.now(timezone.utc).isoformat()
    try:
        return user.client.table("applications").insert(row).execute().data[0], True
    except APIError as exc:
        if exc.code != "23505":
            raise
        # Lost the race against a concurrent call for the same job — the
        # record exists either way, which is all this function promises.
        again = (
            user.client.table("applications")
            .select("*")
            .eq("user_id", user.user_id)
            .eq("job_id", job_id)
            .single()
            .execute()
        )
        return again.data, False


def _apply_status(
    user: AuthedUser, application_id: str, status: str, note: str | None
) -> dict:
    updates: dict = {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}
    if note is not None:
        updates["notes"] = note
    if status == "applied":
        updates["applied_at"] = datetime.now(timezone.utc).isoformat()

    result = (
        user.client.table("applications")
        .update(updates)
        .eq("id", application_id)
        .eq("user_id", user.user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "application not found")
    return result.data[0]


def _write_note(user: AuthedUser, application_id: str, note: str) -> dict:
    result = (
        user.client.table("applications")
        .update({"notes": note, "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", application_id)
        .eq("user_id", user.user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "application not found")
    return result.data[0]


def _with_job(user: AuthedUser, application: dict) -> dict:
    """Re-read one application with its listing embedded, so single-record
    responses carry the same shape as the list endpoint."""
    result = (
        user.client.table("applications")
        .select(_WITH_JOB)
        .eq("id", application["id"])
        .eq("user_id", user.user_id)
        .maybe_single()
        .execute()
    )
    return result.data if result is not None else application


def _place_structure(user: AuthedUser, application: dict, status: str) -> None:
    """Every status transition grows the user's plot by one structure."""
    plot = (
        user.client.table("world_plots")
        .select("origin_x,origin_y")
        .eq("user_id", user.user_id)
        .single()
        .execute()
        .data
    )
    count = (
        user.client.table("world_structures")
        .select("id", count="exact")
        .eq("user_id", user.user_id)
        .execute()
        .count
        or 0
    )
    grid_x, grid_y = structure_position((plot["origin_x"], plot["origin_y"]), count)
    user.client.table("world_structures").insert(
        {
            "user_id": user.user_id,
            "application_id": application["id"],
            "type": structure_type_for_status(status),
            "grid_x": grid_x,
            "grid_y": grid_y,
        }
    ).execute()
