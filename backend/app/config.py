"""
backend/app/config.py
Loads all application settings from the .env file using pydantic-settings.
Changing DATABASE_URL to a PostgreSQL URL is the only change needed
to migrate from SQLite to PostgreSQL.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
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

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
