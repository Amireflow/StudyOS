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
    ai_key_encryption_key: str = ""
    ai_key_encryption_fallback_keys: str = ""
    database_url: str = "sqlite:///./amireflow_local.db"
    frontend_origin: str = "http://localhost:5173"
    frontend_dist_dir: str = ""
    render_external_url: str = ""
    allow_local_dev_auth: bool = True
    allow_insecure_local_ai_url: bool = False
    default_local_user_id: str = "00000000-0000-0000-0000-000000000001"
    default_timezone: str = "Africa/Dakar"
    auth_jwks_url: str = "https://rzjjcqmsepxtpmqwzwmf.supabase.co/auth/v1/.well-known/jwks.json"
    auth_issuer: str = "https://rzjjcqmsepxtpmqwzwmf.supabase.co/auth/v1"
    auth_audience: str = "authenticated"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 14 * 86400
    auth_cookie_name: str = "amireflow_refresh_token"
    auth_cookie_samesite: str = ""
    trusted_proxy_ips: str = ""
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
        origins = [
            item.strip().rstrip("/")
            for item in self.frontend_origin.split(",")
            if item.strip().rstrip("/")
        ]
        render_url = (self.render_external_url or "").strip().rstrip("/")
        if render_url and render_url not in origins:
            origins.append(render_url)
        return origins or ["http://localhost:5173"]

    @property
    def trusted_proxy_list(self) -> list[str]:
        return [item.strip() for item in self.trusted_proxy_ips.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
