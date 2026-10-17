import time

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from postgrest.exceptions import APIError
from supabase import Client

from app.core.auth import (
    InvalidCredentials,
    decode_web_jwt,
    mint_impersonation_jwt,
    resolve_personal_access_token,
)
from app.core.supabase import service_client, user_client
from app.services.identity import generate_username
from app.services.world import allocate_plot

bearer_scheme = HTTPBearer()


class AuthedUser:
    def __init__(self, user_id: str, client: Client):
        self.user_id = user_id
        self.client = client


def _authenticate(raw_token: str) -> tuple[str, str]:
    """Returns (user_id, jwt_to_use_for_postgrest).

    Tries the token as a Supabase web session JWT first; if it doesn't
    decode as one, falls back to treating it as an MCP personal access
    token and mints a short-lived impersonation JWT for whoever it
    resolves to.
    """
    try:
        claims = decode_web_jwt(raw_token)
        return claims["sub"], raw_token
    except jwt.PyJWTError:
        pass

    try:
        user_id = resolve_personal_access_token(raw_token, service_client())
    except InvalidCredentials as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return user_id, mint_impersonation_jwt(user_id)


def _profile_exists(user_id: str, client: Client) -> bool:
    # maybe_single().execute() returns None outright (not a response with
    # .data = None) when zero rows match — not an APIResponse in that case.
    for attempt in range(3):
        try:
            return (
                client.table("profiles").select("id").eq("id", user_id).maybe_single().execute()
                is not None
            )
        except APIError as exc:
            # A freshly issued, already verified web JWT can briefly be
            # ahead of PostgREST's clock. Retry only this initial read;
            # never relax signature/expiry validation or retry writes.
            if exc.code != "PGRST303" or exc.message != "JWT issued at future" or attempt == 2:
                raise
            time.sleep(0.5)
    return False  # unreachable, but keeps the return type explicit


def _ensure_profile_and_plot(user_id: str, client: Client) -> None:
    """Lazily creates the profile + world plot on a user's first
    authenticated request, rather than relying on a database trigger —
    keeps the plot-allocation math in one place (Python) instead of
    duplicating it in plpgsql.

    Idempotent under concurrent calls on purpose: a page's layout and the
    page itself both fetch server data for the same brand-new user at
    nearly the same instant (Next.js runs sibling Server Components'
    fetches in parallel), so two requests can both see "no profile yet"
    and both try to insert. A 23505 here is therefore ambiguous — it
    could be a genuine username collision (retry with a new one) or
    another request winning that exact race (not a failure at all, the
    profile exists either way) — so every conflict re-checks by id before
    deciding which it was, instead of assuming it's always the former.
    """
    created = _profile_exists(user_id, client)
    for _ in range(5):
        if created:
            break
        try:
            client.table("profiles").insert(
                {"id": user_id, "username": generate_username()}
            ).execute()
            created = True
            break
        except APIError as exc:
            if exc.code != "23505":
                raise
            if _profile_exists(user_id, client):
                created = True
                break
            continue  # a real username collision — retry with a new one
    if not created:
        raise RuntimeError("could not allocate a unique username after 5 attempts")

    # Profile creation can succeed while plot creation fails. Always repair
    # that partial state, and distinguish coordinate collisions from an
    # already-created plot. Counts alone can reuse occupied coordinates
    # after an account is deleted.
    for _ in range(10):
        if client.table("world_plots").select("user_id").eq(
            "user_id", user_id
        ).maybe_single().execute() is not None:
            return
        n = client.table("world_plots").select("user_id", count="exact").execute().count or 0
        while True:
            origin_x, origin_y = allocate_plot(n)
            occupied = client.table("world_plots").select("user_id").eq(
                "origin_x", origin_x
            ).eq("origin_y", origin_y).maybe_single().execute()
            if occupied is None:
                break
            n += 1
        try:
            client.table("world_plots").insert(
                {"user_id": user_id, "origin_x": origin_x, "origin_y": origin_y}
            ).execute()
            return
        except APIError as exc:
            if exc.code != "23505":
                raise
    raise RuntimeError("could not allocate a world plot after 10 attempts")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthedUser:
    user_id, effective_jwt = _authenticate(credentials.credentials)
    client = user_client(effective_jwt)
    _ensure_profile_and_plot(user_id, client)
    return AuthedUser(user_id=user_id, client=client)
