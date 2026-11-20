from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres applicatifs chargés depuis l'environnement ou le fichier .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    app_secret_key: str = "local-dev-secret-key-change-me-32bytes"
    database_url: str = "sqlite:///./amireflow_local.db"
    frontend_origin: str = "http://localhost:5173"
    allow_local_dev_auth: bool = True
    default_local_user_id: str = "00000000-0000-0000-0000-000000000001"
    default_timezone: str = "Africa/Dakar"
    auth_jwks_url: str = "https://rzjjcqmsepxtpmqwzwmf.supabase.co/auth/v1/.well-known/jwks.json"
    auth_issuer: str = "https://rzjjcqmsepxtpmqwzwmf.supabase.co/auth/v1"
    auth_audience: str = "authenticated"
    ai_provider: str = "local"
    ai_api_key: str = ""
    ai_model: str = "local-coach-v1"
    ai_base_url: str = ""
    ai_timeout_seconds: float = 20.0
    ai_max_message_chars: int = 2000
    ai_rate_limit_per_minute: int = 30
    timetable_import_max_bytes: int = 10 * 1024 * 1024
    timetable_import_rate_limit_per_minute: int = 15

    @property
    def cors_origins(self) -> list[str]:
        origins = [item.strip() for item in self.frontend_origin.split(",") if item.strip()]
        return origins or ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
