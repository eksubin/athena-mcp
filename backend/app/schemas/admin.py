from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.invite import InviteRole
from app.schemas.profile import Avatar


class AdminAccount(BaseModel):
    id: str
    username: str
    email: str
    real_name: str | None = None
    avatar: Avatar = "fox"
    role: InviteRole
    disabled_at: datetime | None = None
    invite_limit: int
    invites_used: int
    application_count: int
    created_at: datetime
    last_sign_in_at: datetime | None = None


class AdminAccountUpdate(BaseModel):
    """Every field optional: the panel sends only what the admin changed."""

    role: InviteRole | None = None
    # True withdraws access — the account keeps its data and its sessions
    # stay cryptographically valid, but every request is refused (see
    # app/api/deps.get_current_user).
    disabled: bool | None = None
    invite_limit: int | None = Field(default=None, ge=0, le=1000)


class AdminOverview(BaseModel):
    members: int
    admins: int
    disabled: int
    pending_invites: int
