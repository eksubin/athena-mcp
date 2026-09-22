from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import AuthedUser, get_current_user
from app.schemas.application import ApplicationCreate, ApplicationOut, ApplicationStatusUpdate
from app.services.world import structure_position, structure_type_for_status

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    status: str | None = None, user: AuthedUser = Depends(get_current_user)
) -> list[dict]:
    query = user.client.table("applications").select("*").eq("user_id", user.user_id)
    if status:
        query = query.eq("status", status)
    return query.order("updated_at", desc=True).execute().data


@router.post("", response_model=ApplicationOut)
def create_application(
    body: ApplicationCreate, user: AuthedUser = Depends(get_current_user)
) -> dict:
    result = (
        user.client.table("applications")
        .insert({"user_id": user.user_id, "job_id": body.job_id, "status": "saved"})
        .execute()
    )
    application = result.data[0]
    _place_structure(user, application, "saved")
    return application


@router.patch("/{application_id}", response_model=ApplicationOut)
def update_status(
    application_id: str,
    body: ApplicationStatusUpdate,
    user: AuthedUser = Depends(get_current_user),
) -> dict:
    updates: dict = {"status": body.status, "updated_at": datetime.now(timezone.utc).isoformat()}
    if body.note is not None:
        updates["notes"] = body.note
    if body.status == "applied":
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
    application = result.data[0]
    _place_structure(user, application, body.status)
    return application


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
