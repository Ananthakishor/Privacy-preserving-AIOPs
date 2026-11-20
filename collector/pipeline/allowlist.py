"""
collector/pipeline/allowlist.py
Applies the strict metadata allow-list before transmission.

This is the FINAL privacy gate. Only fields in ALLOWED_FIELDS are
permitted to leave the collector environment. All other fields are
dropped regardless of their content.

This prevents "field-creep" — accidentally sending new fields that
weren't intended for the SaaS backend.

The allow-list matches exactly what TelemetryIngestPayload accepts.
"""

# The EXACT set of fields that may be transmitted to the SaaS backend.
# This matches the TelemetryIngestPayload schema in backend/app/schemas/telemetry.py
ALLOWED_FIELDS = {
    "tenant_id",
    "source_id",          # Pseudonymous identifier
    "event_id",           # UUID for idempotent delivery
    "utc_timestamp",      # ISO-8601 UTC, transmission time
    "event_time",         # ISO-8601 UTC, original event time
    "source_timezone",    # IANA timezone string
    "metric_category",    # cpu|memory|disk|network|security
    "metric_value",       # Numeric value
    "severity",           # info|warning|critical|resolved
    "health_status",      # excellent|good|fair|poor
    "alert_context",      # Short text, max 200 chars, pre-screened
    "collector_id",       # Which collector sent this
    # Transparency tag — explicitly approved to leave the collector.
    # Tells SaaS whether data is live/seed/simulated for dashboard labeling.
    # This is NOT sensitive — it describes data quality, not data content.
    "data_source",        # live|seed|simulated
}


def apply_allowlist(event: dict) -> dict:
    """
    Return a new dict containing ONLY the allowed fields.

    Any field not in ALLOWED_FIELDS is silently dropped.
    This is an explicit inclusion list, not an exclusion list —
    we never accidentally leak a new field by forgetting to exclude it.
    """
    approved = {}
    for field in ALLOWED_FIELDS:
        if field in event:
            value = event[field]
            # Enforce max length on alert_context
            if field == "alert_context" and isinstance(value, str):
                value = value[:200]
            approved[field] = value
        else:
            # Field is missing — use safe default rather than failing
            if field == "severity":
                approved[field] = "info"
            elif field == "health_status":
                approved[field] = "excellent"
            elif field == "alert_context":
                approved[field] = ""
            elif field == "source_timezone":
                approved[field] = "UTC"

    return approved


def get_allowed_fields() -> list:
    """Return the sorted list of allowed field names (for egress proof display)."""
    return sorted(ALLOWED_FIELDS)
