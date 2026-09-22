import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.api.deps import AuthedUser, get_current_user
from app.core.config import get_settings
from app.schemas.resume import ProfileFactOut, ResumeOut

router = APIRouter(prefix="/resumes", tags=["resumes"])

_ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt"}


@router.post("", response_model=ResumeOut)
async def upload_resume(file: UploadFile, user: AuthedUser = Depends(get_current_user)) -> dict:
    """Stores the file on the VPS's local volume and records the row.

    Turning the file into `profile_facts` is a separate parsing step, not
    implemented yet — this endpoint only handles storage and lets
    /profile-facts be populated (by a future parser, or manually) afterward.
    """
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
    return result.data[0]


@router.get("/{resume_id}/facts", response_model=list[ProfileFactOut])
def get_resume_facts(resume_id: str, user: AuthedUser = Depends(get_current_user)) -> list[dict]:
    result = (
        user.client.table("profile_facts")
        .select("key,value,confidence")
        .eq("source_resume_id", resume_id)
        .execute()
    )
    return result.data
