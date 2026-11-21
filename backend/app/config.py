"""
backend/app/config.py
Loads all application settings from the .env file using pydantic-settings.
Changing DATABASE_URL to a PostgreSQL URL is the only change needed
to migrate from SQLite to PostgreSQL.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal
from pydantic import model_validator


class Settings(BaseSettings):
    app_env: Literal["development", "production"] = "development"

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60

    # Database — SQLite default; swap for PostgreSQL by changing this URL
    database_url: str = "sqlite:///./sentinelops.db"

    # IBM watsonx AI (optional — used only for Ask Sentinel AI assistant)
    ibm_watsonx_api_key: str = ""
    ibm_watsonx_project_id: str = ""
    ibm_watsonx_endpoint: str = ""
    ibm_watsonx_region: str = "us-south"

    # CORS
    frontend_origin: str = "http://localhost:5173"

    # Collector security
    collector_offline_threshold_seconds: int = 60

    # Logging
    log_level: str = "INFO"
    audit_log_file: str = "./logs/audit.jsonl"

    @model_validator(mode="after")
    def validate_production(self):
        if self.app_env == "production":
            if self.frontend_origin not in {
                "https://tesseract.cv",
                "https://sentinelops-frontend-tau.vercel.app",
            }:
                raise ValueError("Set FRONTEND_ORIGIN to the approved Vercel origin")
            if len(self.secret_key.encode()) < 32 or self.secret_key.startswith("change-me"):
                raise ValueError("Set a randomly generated production SECRET_KEY")
            if not self.database_url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
                raise ValueError("Production requires managed PostgreSQL")
        return self

    class Config:
        hide_input_in_errors = True
        env_file = "../.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
