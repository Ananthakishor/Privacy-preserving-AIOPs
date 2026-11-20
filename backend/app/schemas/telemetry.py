"""backend/app/schemas/telemetry.py — Strict allow-list schema for ingest."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class TelemetryIngestPayload(BaseModel):
    """
    The ONLY fields allowed to travel from collector to SaaS backend.
    Any field not listed here is rejected at schema validation (422).
    This is the allow-list enforcement at the API boundary.
    """
    tenant_id: str
    source_id: str                              # Pseudonymous identifier
    event_id: str                               # UUID — idempotency key
    utc_timestamp: str                          # ISO-8601 UTC, transmission time
    event_time: str                             # ISO-8601 UTC, original event time
    source_timezone: str = "UTC"               # IANA timezone
    metric_category: str                        # cpu|memory|disk|network|security
    metric_value: float
    severity: str = "info"                      # info|warning|critical|resolved
    health_status: str = "excellent"            # excellent|good|fair|poor
    alert_context: str = Field(default="", max_length=200)  # Pre-screened, max 200 chars
    collector_id: str

    @field_validator("metric_category")
    @classmethod
    def validate_category(cls, v):
        allowed = {"cpu", "memory", "disk", "network", "security"}
        if v not in allowed:
            raise ValueError(f"metric_category must be one of {allowed}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v):
        allowed = {"info", "warning", "critical", "resolved"}
        if v not in allowed:
            raise ValueError(f"severity must be one of {allowed}")
        return v

    @field_validator("health_status")
    @classmethod
    def validate_health(cls, v):
        allowed = {"excellent", "good", "fair", "poor"}
        if v not in allowed:
            raise ValueError(f"health_status must be one of {allowed}")
        return v


class MetricResponse(BaseModel):
    id: str
    source_id: str
    category: str
    value: float
    utc_timestamp: str
    event_time: str

    class Config:
        from_attributes = True
