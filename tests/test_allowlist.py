"""
tests/test_allowlist.py
Test 1: Verify field allow-list enforcement.
Only ALLOWED_FIELDS may be in the approved payload.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from collector.pipeline.allowlist import apply_allowlist, ALLOWED_FIELDS


def test_only_allowed_fields_in_output():
    """Non-allow-listed fields must be dropped."""
    raw = {
        "tenant_id": "tenant-alpha",
        "source_id": "src-001",
        "event_id": "test-uuid",
        "utc_timestamp": "2026-01-01T00:00:00+00:00",
        "event_time": "2026-01-01T00:00:00+00:00",
        "source_timezone": "UTC",
        "metric_category": "cpu",
        "metric_value": 45.0,
        "severity": "info",
        "health_status": "excellent",
        "alert_context": "",
        "collector_id": "col-01",
        # Non-allowed fields that must be dropped:
        "hostname": "web-server-01",          # real hostname
        "password": "secret123",               # credential
        "_raw_log": "auth failure for root",   # raw log
        "process_list": ["nginx", "python"],   # process info
        "extra_field": "should be dropped",
    }
    result = apply_allowlist(raw)

    # Only allowed fields should remain
    for key in result.keys():
        assert key in ALLOWED_FIELDS, f"Non-allowed field '{key}' found in approved payload"

    # Required fields should be present
    assert "tenant_id" in result
    assert "event_id" in result
    assert "metric_value" in result

    # Sensitive fields must NOT be present
    assert "hostname" not in result
    assert "password" not in result
    assert "_raw_log" not in result
    assert "process_list" not in result
    assert "extra_field" not in result


def test_alert_context_max_length():
    """alert_context must be capped at 200 characters."""
    raw = {
        "tenant_id": "t", "source_id": "s", "event_id": "e",
        "utc_timestamp": "2026-01-01T00:00:00+00:00",
        "event_time": "2026-01-01T00:00:00+00:00", "source_timezone": "UTC",
        "metric_category": "cpu", "metric_value": 10.0,
        "severity": "info", "health_status": "excellent",
        "collector_id": "c",
        "alert_context": "A" * 500,  # Too long
    }
    result = apply_allowlist(raw)
    assert len(result["alert_context"]) <= 200


def test_missing_fields_get_safe_defaults():
    """Missing optional fields get safe defaults rather than failing."""
    minimal = {
        "tenant_id": "t", "source_id": "s", "event_id": "e",
        "utc_timestamp": "2026-01-01T00:00:00+00:00",
        "event_time": "2026-01-01T00:00:00+00:00",
        "metric_category": "cpu", "metric_value": 10.0, "collector_id": "c",
    }
    result = apply_allowlist(minimal)
    assert result["severity"] == "info"
    assert result["health_status"] == "excellent"
    assert result["alert_context"] == ""
