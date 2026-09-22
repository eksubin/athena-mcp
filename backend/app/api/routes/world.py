from fastapi import APIRouter, Depends

from app.api.deps import AuthedUser, get_current_user
from app.schemas.world import PlotOut, StructureOut

router = APIRouter(prefix="/world", tags=["world"])


@router.get("/plots", response_model=list[PlotOut])
def list_plots(user: AuthedUser = Depends(get_current_user)) -> list[dict]:
    """Public map data: plot positions plus username/avatar only — never
    joins anything from `applications` or `jobs`."""
    plots = user.client.table("world_plots").select("user_id,origin_x,origin_y").execute().data
    user_ids = [p["user_id"] for p in plots]
    if not user_ids:
        return []

    profiles = (
        user.client.table("public_profiles")
        .select("id,username,avatar_seed")
        .in_("id", user_ids)
        .execute()
        .data
    )
    by_id = {p["id"]: p for p in profiles}
    return [
        {
            "user_id": p["user_id"],
            "origin_x": p["origin_x"],
            "origin_y": p["origin_y"],
            "username": by_id[p["user_id"]]["username"],
            "avatar_seed": by_id[p["user_id"]]["avatar_seed"],
        }
        for p in plots
        if p["user_id"] in by_id
    ]


@router.get("/structures", response_model=list[StructureOut])
def list_structures(user: AuthedUser = Depends(get_current_user)) -> list[dict]:
    result = user.client.table("world_structures").select("id,user_id,type,grid_x,grid_y").execute()
    return result.data
