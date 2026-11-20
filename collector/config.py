"""
collector/config.py
Loads collector configuration from the root .env file.
"""
import os
from dotenv import load_dotenv

# Load .env from parent directory (project root)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


class CollectorConfig:
    # Where to send approved metadata
    SAAS_INGEST_URL: str = os.getenv("SAAS_INGEST_URL", "http://localhost:8000/api/v1/telemetry/ingest")
    SAAS_HEARTBEAT_URL: str = os.getenv("SAAS_HEARTBEAT_URL", "http://localhost:8000/api/v1/collectors/heartbeat")

    # Collector identity and authentication
    COLLECTOR_API_KEY: str = os.getenv("COLLECTOR_API_KEY", "collector-secret-key-cicada2026")
    COLLECTOR_TENANT_ID: str = os.getenv("COLLECTOR_TENANT_ID", "tenant-alpha")
    COLLECTOR_SOURCE_ID: str = os.getenv("COLLECTOR_SOURCE_ID", "src-server-01")
    COLLECTOR_REGION: str = os.getenv("COLLECTOR_REGION", "us-south")
    COLLECTOR_VERSION: str = "1.0.0"

    # Timing
    EMIT_INTERVAL_SECONDS: int = int(os.getenv("SIMULATOR_EMIT_INTERVAL_SECONDS", "5"))
    HEARTBEAT_INTERVAL_SECONDS: int = int(os.getenv("COLLECTOR_HEARTBEAT_INTERVAL_SECONDS", "15"))

    # Retry behavior
    RETRY_MAX_ATTEMPTS: int = int(os.getenv("COLLECTOR_RETRY_MAX_ATTEMPTS", "10"))
    RETRY_BASE_DELAY: float = float(os.getenv("COLLECTOR_RETRY_BASE_DELAY_SECONDS", "2"))

    # Local storage
    LOCAL_DB_PATH: str = os.getenv("COLLECTOR_DB_URL", "sqlite:///./collector_buffer.db").replace("sqlite:///", "")
    EGRESS_LOG_PATH: str = os.path.join(os.path.dirname(__file__), "egress_proof", "egress.jsonl")

    # Local UI (egress proof viewer — never accessible from SaaS)
    LOCAL_UI_PORT: int = int(os.getenv("COLLECTOR_LOCAL_UI_PORT", "8001"))


config = CollectorConfig()
