from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Desktop MCP clients may launch from a different project directory.
    model_config = SettingsConfigDict(
        env_prefix="ATHENA_", env_file=Path(__file__).resolve().parents[1] / ".env", extra="ignore"
    )

    api_url: str = "http://localhost:8000"
    # Personal access token, issued from the web app's /settings page.
    token: str
