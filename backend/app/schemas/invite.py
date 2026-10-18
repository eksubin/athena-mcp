import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

InviteRole = Literal["member", "admin"]

# Deliberately not pydantic's EmailStr: that pulls in email-validator for
# RFC-level parsing Athena has no use for. The address only has to be
# plausible enough to send an invite to, and the database applies the same
# shape check (see invites_guard_insert) — this is for a useful error
# message, not for authority.
_EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")


def normalize_email(value: str) -> str:
    """Lower-cased and trimmed, matching how GoTrue stores addresses — the
    signup gate matches an invite to an account by equality, so an invite
    typed as "Someone@Example.com" has to normalize the same way."""
    email = value.strip().lower()
    if not _EMAIL_SHAPE.match(email):
        raise ValueError("Enter a valid email address")
    return email


class InviteCreate(BaseModel):
    email: str
    note: str | None = None

    _normalize = field_validator("email")(normalize_email)


class AdminInviteCreate(InviteCreate):
    # Only an admin can hand out admin access; the database enforces the
    # same rule independently (invites_guard_insert).
    role: InviteRole = "member"


class InviteOut(BaseModel):
    id: str
    email: str
    role: InviteRole
    note: str | None = None
    created_at: datetime
    revoked_at: datetime | None = None
    accepted_at: datetime | None = None
    accepted_user_id: str | None = None


class AdminInviteOut(InviteOut):
    invited_by: str | None = None
    invited_by_username: str | None = None
    accepted_username: str | None = None
