from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ATHENA_", env_file=".env", extra="ignore")

    api_url: str = "http://localhost:8000"
    # Personal access token, issued from the web app's /settings page.
    token: str
