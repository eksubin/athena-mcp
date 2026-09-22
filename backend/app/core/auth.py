import hashlib
import secrets
import time
from datetime import datetime, timezone
from functools import lru_cache

import jwt
from supabase import Client

from app.core.config import get_settings

# Real user sessions from this project are signed ES256 by GoTrue — verified
# by actually decoding a live, GoTrue-issued session token's header, not
# assumed. But PostgREST here accepts EITHER that ES256 key OR the legacy
# HS256 shared secret (also verified live: a token minted with the secret
# was accepted as a real authenticated session) — a normal transitional
# setup. So: verify incoming web tokens via JWKS/ES256 (that's what real
# sessions actually are), but keep minting impersonation tokens with the
# legacy HS256 secret for the MCP path, since PostgREST is proven to accept
# both and nobody but Supabase holds the ES256 private key to mint with.
AUDIENCE = "authenticated"
IMPERSONATION_TTL_SECONDS = 300


class InvalidCredentials(Exception):
    pass


@lru_cache
def _jwk_client() -> jwt.PyJWKClient:
    settings = get_settings()
    return jwt.PyJWKClient(f"{settings.supabase_url}/auth/v1/.well-known/jwks.json")


def decode_web_jwt(token: str) -> dict:
    """Verify a Supabase session JWT from the web app against the
    project's published public signing key."""
    signing_key = _jwk_client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256", "RS256"],
        audience=AUDIENCE,
    )


def mint_impersonation_jwt(user_id: str) -> str:
    """Sign a short-lived Supabase-shaped JWT for `user_id`.

    The MCP server can't do an OAuth redirect, so it authenticates with a
    personal access token instead. Once that token is resolved to a
    user_id, this mints a short-lived HS256 token signed with the legacy
    secret — not a real GoTrue session (only Supabase holds the ES256
    private key for that), but PostgREST is configured to accept either,
    so RLS still enforces access on this path exactly as it does on the
    real-session path, instead of the API layer reimplementing the checks.
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
    return jwt.encode(payload, settings.supabase_jwt_secret, algorithm="HS256")


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
