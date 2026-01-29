from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore


class Settings(BaseSettings):
    # Security
    WHITELIST_FILE: str = "allowed_domains.json"
    ALLOWED_DOMAINS_ENV: str = ""  # Comma-separated list of allowed domains from env

    # Public URL for the API (used in JS injection)
    PUBLIC_API_URL: str = "http://localhost:8000/graph"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
