"""Application configuration. All secrets come from environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI Growth Sales Engine"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://age:age@localhost:5432/age"
    secret_key: str = "change-me"
    access_token_minutes: int = 60 * 12
    cors_origins: str = "http://localhost:5173"
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    allow_registration: bool = True
    trust_proxy_headers: bool = False  # true only behind our Nginx
    db_auto_create: bool = True  # dev convenience; Docker sets false and runs Alembic

    # AI
    ai_provider: str = "anthropic"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    ai_max_concurrency: int = 2
    ai_max_retries: int = 2

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # Email notifications (optional, to the user only)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def google_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def google_redirect_uri(self) -> str:
        return f"{self.backend_url.rstrip('/')}/api/integrations/google/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()
