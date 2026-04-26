from typing import Any, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # App
    app_name: str = "AI Agent Orchestration Platform"
    environment: str = "development"
    secret_key: str = "dev-secret-key-change-in-prod"
    # Set DEBUG=false in Docker to quiet SQLAlchemy engine echo
    debug: bool = True

    @field_validator("openai_api_key", "anthropic_api_key", "telegram_bot_token", "telegram_webhook_url", mode="before")
    @classmethod
    def _empty_secrets_to_none(cls, v: Any) -> Any:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return v

    @field_validator("debug", mode="before")
    @classmethod
    def _coerce_debug(cls, v: Any) -> bool:
        if v is None:
            return True
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("0", "false", "no", "off", ""):
                return False
            if s in ("1", "true", "yes", "on"):
                return True
        return bool(v)

    # Database
    database_url: str = "postgresql+asyncpg://orchestrator:orchestrator_pass@localhost:5432/agentdb"
    database_url_sync: str = "postgresql://orchestrator:orchestrator_pass@localhost:5432/agentdb"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # AI Providers
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: Optional[str] = None

    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_webhook_url: Optional[str] = None

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


settings = Settings()
