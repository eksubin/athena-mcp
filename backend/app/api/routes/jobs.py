from fastapi import APIRouter, Depends

from app.api.deps import AuthedUser, get_current_user
from app.schemas.job import JobDetail, JobSummary
from app.services.scoring import score_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobSummary])
def search_jobs(limit: int = 10, user: AuthedUser = Depends(get_current_user)) -> list[dict]:
    """This is the endpoint search_jobs (MCP) calls — the whole point of it
    is to return a short, ranked list instead of a full listings dump."""
    limit = min(limit, 20)
    profile = (
        user.client.table("profiles").select("preferences").eq("id", user.user_id).single().execute()
    ).data
    preferences = (profile or {}).get("preferences", {})

    jobs = (
        user.client.table("jobs").select("*").order("ingested_at", desc=True).limit(100).execute()
    ).data

    scored = []
    for job in jobs:
        score, signals = score_job(job, preferences)
        user.client.table("job_scores").upsert(
            {"job_id": job["id"], "user_id": user.user_id, "score": score, "signals": signals},
            on_conflict="job_id,user_id",
        ).execute()
        scored.append({**job, "score": score})

    scored.sort(key=lambda j: j["score"], reverse=True)
    return scored[:limit]


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: str, user: AuthedUser = Depends(get_current_user)) -> dict:
    job = user.client.table("jobs").select("*").eq("id", job_id).single().execute().data
    score_row = (
        user.client.table("job_scores")
        .select("score")
        .eq("job_id", job_id)
        .eq("user_id", user.user_id)
        .maybe_single()
        .execute()
    )
    # maybe_single().execute() returns None outright (not a response with
    # .data = None) when this user has no score for the job yet.
    job["score"] = score_row.data["score"] if score_row is not None else None
    return job
