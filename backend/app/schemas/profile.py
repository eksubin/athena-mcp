import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

# The five drawings live in the web app; the database stores only which one
# was chosen (see supabase/migrations/0003_profile_identity.sql).
Avatar = Literal["fox", "owl", "cat", "bear", "fawn"]

# Lower-case letters, digits and single inner hyphens, starting with a
# letter. Kept deliberately narrow: this handle is the one thing other
# people see on the shared map. Mirrors the database's own check
# constraint — this exists for the error message, not for the authority.
_USERNAME_SHAPE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


class ProfileOut(BaseModel):
    id: str
    username: str
    avatar_seed: str
    avatar: Avatar = "fox"
    real_name: str | None = None
    preferences: dict = {}
    # Read-only here on purpose — these three are set from the invite that
    # admitted the account and are thereafter writable only by the admin
    # endpoints (trigger-enforced; see
    # supabase/migrations/0002_invites_and_admin.sql). ProfileUpdate
    # deliberately does not accept them.
    role: Literal["member", "admin"] = "member"
    invite_limit: int = 0
    disabled_at: datetime | None = None


class ProfileUpdate(BaseModel):
    real_name: str | None = None
    preferences: dict | None = None
    username: str | None = None
    avatar: Avatar | None = None

    @field_validator("username")
    @classmethod
    def _check_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        username = value.strip().lower()
        if not 3 <= len(username) <= 24:
            raise ValueError("Pick a name between 3 and 24 characters")
        if not _USERNAME_SHAPE.match(username):
            raise ValueError(
                "Use lowercase letters, numbers and hyphens, starting with a letter"
            )
        return username
