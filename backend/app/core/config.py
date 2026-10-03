from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = "sqlite:///./ai_confidence.db"

    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str | None = None
    factual_search_model: str = "gpt-4.1-mini"

    consistency_samples: int = 5
    fusion_method: str = "weighted"
    step_calibrator_path: str | None = None

    frontend_url: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()