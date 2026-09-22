from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    # Writing to the shared `jobs` catalog bypasses RLS by design — see
    # supabase/migrations/0001_init.sql: only the service role may write
    # there, everyone else gets read-only.
    supabase_service_role_key: str

    # Seconds between ingestion runs. The HN thread only gets new top-level
    # comments for the first week or so of each month; once a day is
    # already generous.
    interval_seconds: int = 86400
