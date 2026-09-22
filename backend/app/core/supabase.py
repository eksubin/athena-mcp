from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def service_client() -> Client:
    """Bypasses RLS entirely. Only for: resolving a personal access token to
    a user_id, and (from Phase 3) the ingestion worker writing to `jobs`.
    Never used on a path a client's own data flows through. Safe to cache —
    unlike `user_client`, its identity doesn't change per request."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def user_client(jwt: str) -> Client:
    """A Supabase client scoped to one user's JWT, so every query it makes is
    subject to that user's Row Level Security policies — this is where
    authorization actually happens, not in route handlers. Built fresh per
    request/token; never cache or share this across requests."""
    settings = get_settings()
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(jwt)
    return client
