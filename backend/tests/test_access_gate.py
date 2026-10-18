"""The invite-only gate as it applies to accounts that already exist.

The database refuses to create an uninvited account (see
supabase/migrations/0002_invites_and_admin.sql), but it cannot refuse a
*session*: a suspended account's GoTrue cookie and personal access tokens
stay cryptographically valid until they expire. So withdrawing access has
to be checked per request, which is what these cover.
"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api import deps


@pytest.fixture
def authenticated(monkeypatch):
    """Everything up to the access check, stubbed: a valid credential for
    'user' whose profile is whatever the test hands back."""

    def configure(profile):
        monkeypatch.setattr(deps, "_authenticate", lambda raw: ("user", "jwt"))
        monkeypatch.setattr(deps, "user_client", lambda jwt: SimpleNamespace(jwt=jwt))
        monkeypatch.setattr(
            deps, "_ensure_profile_and_plot", lambda user_id, client: profile
        )
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")

    return configure


def test_active_member_is_let_in(authenticated):
    credentials = authenticated({"id": "user", "role": "member", "disabled_at": None})
    user = deps.get_current_user(credentials)
    assert user.user_id == "user"
    assert user.is_admin is False


def test_admin_role_is_carried_through(authenticated):
    credentials = authenticated({"id": "user", "role": "admin", "disabled_at": None})
    assert deps.get_current_user(credentials).is_admin is True


def test_suspended_account_is_refused_despite_a_valid_session(authenticated):
    credentials = authenticated(
        {"id": "user", "role": "member", "disabled_at": "2026-10-17T12:00:00+00:00"}
    )
    with pytest.raises(HTTPException) as refused:
        deps.get_current_user(credentials)
    assert refused.value.status_code == 403


def test_suspension_outranks_the_admin_role(authenticated):
    credentials = authenticated(
        {"id": "user", "role": "admin", "disabled_at": "2026-10-17T12:00:00+00:00"}
    )
    with pytest.raises(HTTPException):
        deps.get_current_user(credentials)


def test_admin_endpoints_refuse_a_member():
    member = deps.AuthedUser("user", client=None, role="member")
    with pytest.raises(HTTPException) as refused:
        deps.get_admin_user(member)
    assert refused.value.status_code == 403


def test_admin_endpoints_accept_an_admin():
    admin = deps.AuthedUser("user", client=None, role="admin")
    assert deps.get_admin_user(admin) is admin


def test_missing_role_defaults_to_member(authenticated):
    """A profile row from before the migration has no role column value to
    read; it must not be treated as privileged."""
    credentials = authenticated({"id": "user"})
    assert deps.get_current_user(credentials).role == "member"
