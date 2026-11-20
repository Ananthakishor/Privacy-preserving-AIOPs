"""backend/app/schemas/telemetry.py — Strict allow-list schema for ingest."""
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from pydantic import ConfigDict


class TelemetryIngestPayload(BaseModel):
    """
    The ONLY fields allowed to travel from collector to SaaS backend.
    Any field not listed here is rejected at schema validation (422).
    This is the allow-list enforcement at the API boundary.

    data_source is an optional transparency tag added in hackathon v2:
      "live"      — real psutil/ICMP measurement from actual hardware
      "seed"      — synthetic seed data inserted for baseline warm-up
      "simulated" — injected by the telemetry simulator for demos
    This tag helps judges and operators understand data provenance at a glance.
    It is NOT sensitive — it is explicitly allowed to leave the collector.
    """
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

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
    # Transparency tag — safe to transmit, not sensitive
    data_source: Literal["live", "seed", "simulated"] = "live"

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
    data_source: str = "live"

    class Config:
        from_attributes = True
