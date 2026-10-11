import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.api.deps import AuthedUser, get_current_user
from app.core.config import get_settings
from app.schemas.resume import ProfileFactOut, ResumeOut
from app.services.resume_parser import extract_text, parse_facts

router = APIRouter(prefix="/resumes", tags=["resumes"])

_ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt"}


@router.post("", response_model=ResumeOut)
async def upload_resume(file: UploadFile, user: AuthedUser = Depends(get_current_user)) -> dict:
    """Stores the file, records the row, and best-effort parses it into
    `profile_facts` — see app/services/resume_parser.py for what
    "best-effort" means here."""
    settings = get_settings()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(400, f"unsupported file type {suffix!r}")

    resume_id = str(uuid.uuid4())
    user_dir = Path(settings.resume_storage_dir) / user.user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    dest = user_dir / f"{resume_id}{suffix}"
    dest.write_bytes(await file.read())

    result = (
        user.client.table("resumes")
        .insert(
            {
                "id": resume_id,
                "user_id": user.user_id,
                "storage_path": str(dest),
                "original_filename": file.filename,
            }
        )
        .execute()
    )
    resume = result.data[0]

    try:
        text = extract_text(dest, suffix)
        facts = parse_facts(text)
    except Exception:
        # File and row are already saved regardless — a parsing failure
        # (corrupted file, unexpected encoding) shouldn't fail the upload
        # itself. parsed_at stays null, which distinguishes "couldn't even
        # try" from "tried and found nothing" (an empty facts list still
        # gets parsed_at set below).
        return resume

    if facts:
        user.client.table("profile_facts").upsert(
            [{**f, "user_id": user.user_id, "source_resume_id": resume_id} for f in facts],
            on_conflict="user_id,key",
        ).execute()

    updated = (
        user.client.table("resumes")
        .update({"parsed_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", resume_id)
        .execute()
    )
    return updated.data[0]


@router.get("", response_model=list[ResumeOut])
def list_resumes(user: AuthedUser = Depends(get_current_user)) -> list[dict]:
    return (
        user.client.table("resumes")
        .select("id,original_filename,uploaded_at,parsed_at")
        .order("uploaded_at", desc=True)
        .execute()
        .data
    )


@router.get("/{resume_id}/facts", response_model=list[ProfileFactOut])
def get_resume_facts(resume_id: str, user: AuthedUser = Depends(get_current_user)) -> list[dict]:
    result = (
        user.client.table("profile_facts")
        .select("key,value,confidence")
        .eq("source_resume_id", resume_id)
        .execute()
    )
    return result.data
