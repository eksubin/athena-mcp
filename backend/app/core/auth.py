import hashlib
import secrets
import time
from datetime import datetime, timezone

import jwt
from supabase import Client

from app.core.config import get_settings

# This project self-hosts GoTrue (see docker-compose.yml's auth/rest/db/
# gateway services) configured with a single GOTRUE_JWT_SECRET — no
# asymmetric signing keys set up. So real web sessions and our own minted
# MCP-impersonation tokens are both plain HS256, signed with the same
# secret: one verification path covers both. (An earlier version of this
# file targeted Supabase *Cloud*, whose GoTrue signs ES256 by default and
# needed JWKS-based verification — that's gone now that this is
# self-hosted. If this ever points at Cloud again, that distinction
# matters; it doesn't for a self-hosted GOTRUE_JWT_SECRET setup.)
ALGORITHM = "HS256"
AUDIENCE = "authenticated"
IMPERSONATION_TTL_SECONDS = 300


class InvalidCredentials(Exception):
    pass


def decode_web_jwt(token: str) -> dict:
    """Verify a session JWT from the web app."""
    settings = get_settings()
    return jwt.decode(
        token,
        settings.supabase_jwt_secret,
        algorithms=[ALGORITHM],
        audience=AUDIENCE,
    )


def mint_impersonation_jwt(user_id: str) -> str:
    """Sign a short-lived session-shaped JWT for `user_id`.

    The MCP server can't do an OAuth redirect, so it authenticates with a
    personal access token instead. Once that token is resolved to a
    user_id, this mints a real (if short-lived) session token for that
    user — signed with the same secret GoTrue itself uses — so the rest of
    the request goes through PostgREST exactly like a real web session
    would. RLS enforces access either way, instead of the API layer
    reimplementing those checks for a second auth path.
    """
    settings = get_settings()
    now = int(time.time())
    payload = {
        "sub": user_id,
        "role": "authenticated",
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + IMPERSONATION_TTL_SECONDS,
    }
    return jwt.encode(payload, settings.supabase_jwt_secret, algorithm=ALGORITHM)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_personal_access_token() -> tuple[str, str]:
    """Returns (raw_token, hash). Only the hash is ever stored — the raw
    value is shown to the user exactly once, at creation time."""
    raw = f"athena_pat_{secrets.token_urlsafe(32)}"
    return raw, hash_token(raw)


def resolve_personal_access_token(raw_token: str, service_client: Client) -> str:
    """Look up which user a personal access token belongs to.

    Runs against the service-role client because, by definition, we don't
    yet know who the caller is — this is the one lookup in the system that
    has to happen before we know whose data to scope to.
    """
    token_hash = hash_token(raw_token)
    result = (
        service_client.table("access_tokens")
        .select("id,user_id")
        .eq("token_hash", token_hash)
        .maybe_single()
        .execute()
    )
    # maybe_single().execute() returns None outright (not a response with
    # .data = None) when zero rows match.
    if result is None:
        raise InvalidCredentials("unknown or revoked token")
    row = result.data
    service_client.table("access_tokens").update(
        {"last_used_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", row["id"]).execute()
    return row["user_id"]
