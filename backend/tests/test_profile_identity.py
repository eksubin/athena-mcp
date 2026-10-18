"""The shape rules for a username a person picks themselves.

These mirror the database's own check constraint — the profile row is
written with the user's own JWT, so the constraint is the authority and
this is what turns a violation into a sentence someone can act on.
"""

import pytest
from pydantic import ValidationError

from app.schemas.profile import ProfileUpdate


def test_a_plain_handle_is_accepted():
    assert ProfileUpdate(username="quiet-meadow-76").username == "quiet-meadow-76"


def test_case_and_padding_are_normalized_rather_than_refused():
    """The constraint forbids upper case; typing it is a slip, not an error."""
    assert ProfileUpdate(username="  Quiet-Meadow  ").username == "quiet-meadow"


@pytest.mark.parametrize(
    "username",
    [
        "ab",  # too short
        "a" * 25,  # too long
        "9lives",  # must start with a letter
        "-leading",
        "trailing-",
        "double--hyphen",
        "has space",
        "has_underscore",
        "emoji🦊",
        "name@example.com",
    ],
)
def test_handles_that_would_violate_the_constraint_are_refused(username):
    with pytest.raises(ValidationError):
        ProfileUpdate(username=username)


def test_an_update_may_leave_the_username_alone():
    update = ProfileUpdate(real_name="Someone")
    assert update.username is None
    assert update.model_dump(exclude_none=True) == {"real_name": "Someone"}


def test_only_the_five_known_avatars_are_accepted():
    for name in ("fox", "owl", "cat", "bear", "fawn"):
        assert ProfileUpdate(avatar=name).avatar == name
    with pytest.raises(ValidationError):
        ProfileUpdate(avatar="dragon")


def test_role_and_access_cannot_be_set_through_a_profile_update():
    """Privilege lives on columns the database protects; the request model
    does not even carry them, so a stray field is dropped rather than
    silently trusted."""
    update = ProfileUpdate.model_validate(
        {"username": "someone-new", "role": "admin", "disabled_at": None, "invite_limit": 999}
    )
    assert update.model_dump(exclude_none=True) == {"username": "someone-new"}
