"""
collector/pipeline/normalizer.py
Converts raw psutil/security data into a consistent internal format.

Normalization:
- Assigns a pseudonymous source_id (never the actual hostname)
- Ensures all timestamps are UTC ISO-8601
- Adds source_timezone
- Splits raw dict into individual metric events
- Each event gets a unique UUID for idempotent delivery
"""
import uuid
from datetime import datetime, timezone
from ..config import config


def normalize_metrics(raw: dict, collector_id: str = None) -> list:
    """
    Convert raw collected data into a list of normalized metric events.
    Each event represents one (source, category, value, timestamp) tuple.

    Returns a list of dicts — one per metric category.
    These still contain the raw host data until the redactor runs.
    """
    now = datetime.now(timezone.utc).isoformat()
    collection_time = raw.get("collection_timestamp", now)

    events = []

    # CPU metric
    if "cpu_percent" in raw:
        events.append(_make_event(
            collector_id=collector_id,
            category="cpu",
            value=raw["cpu_percent"],
            event_time=collection_time,
            extra={"raw_hostname": raw.get("hostname", "unknown")},
        ))

    # Memory metric
    if "memory_percent" in raw:
        events.append(_make_event(
            collector_id=collector_id,
            category="memory",
            value=raw["memory_percent"],
            event_time=collection_time,
            extra={"raw_hostname": raw.get("hostname", "unknown")},
        ))

    # Disk metric
    if "disk_percent" in raw:
        events.append(_make_event(
            collector_id=collector_id,
            category="disk",
            value=raw["disk_percent"],
            event_time=collection_time,
        ))

    # Network latency
    if "simulated_latency_ms" in raw:
        events.append(_make_event(
            collector_id=collector_id,
            category="network",
            value=raw["simulated_latency_ms"],
            event_time=collection_time,
            extra={"metric_subtype": "latency_ms"},
        ))

    # Security signals
    if "failed_login_count" in raw:
        events.append(_make_event(
            collector_id=collector_id,
            category="security",
            value=float(raw["failed_login_count"]),
            event_time=collection_time,
            extra={
                "security_severity": raw.get("security_severity", "info"),
                "security_description": raw.get("security_description", ""),
                # RAW SENSITIVE FIELDS — present here, will be stripped by redactor/allowlist
                "_raw_usernames": raw.get("_raw_usernames_attempted", []),
                "_raw_source_ips": raw.get("_raw_source_ips", []),
            },
        ))

    # Also preserve the raw config snippet field to demonstrate redaction
    if "raw_config_snippet" in raw:
        for event in events:
            event["_raw_config_snippet"] = raw["raw_config_snippet"]

    return events


def _make_event(collector_id: str, category: str, value: float, event_time: str, extra: dict = None) -> dict:
    """Create a single normalized metric event with a unique ID."""
    event = {
        # Fields that WILL be in the outgoing payload
        "event_id": str(uuid.uuid4()),  # Unique ID for idempotent delivery
        "tenant_id": config.COLLECTOR_TENANT_ID,
        "source_id": config.COLLECTOR_SOURCE_ID,  # Pseudonymous — not the real hostname
        "collector_id": collector_id or "collector-local",
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "event_time": event_time,
        "source_timezone": "UTC",
        "metric_category": category,
        "metric_value": round(value, 2),
        "severity": "info",          # Will be updated by health classifier
        "health_status": "excellent", # Will be updated by health classifier
        "alert_context": "",
    }
    if extra:
        event.update(extra)
    return event
