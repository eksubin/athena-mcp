from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Desktop MCP clients launch this server from whatever directory they
    # happen to be in, so the .env path is resolved from the package
    # rather than the working directory: parents[1] is the repository root
    # in a checkout. Installed copies (uvx, pipx) have no .env to find and
    # take both values from the client config's "env" block instead;
    # environment variables win over the file either way.
    model_config = SettingsConfigDict(
        env_prefix="ATHENA_", env_file=Path(__file__).resolve().parents[1] / ".env", extra="ignore"
    )

    api_url: str = "http://localhost:8000"
    # Personal access token, issued from the web app's /settings page.
    token: str
