from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    # Project Settings > API > JWT Secret in the Supabase dashboard. Used both
    # to verify JWTs from the web app and to mint short-lived impersonation
    # JWTs when a request authenticates with a personal access token instead.
    supabase_jwt_secret: str

    # Where CV files land on the VPS's local volume (see spec section 07).
    resume_storage_dir: str = "/data/resumes"

    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
