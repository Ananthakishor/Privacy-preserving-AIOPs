"""
tests/test_secret_filter.py
Test 2: Verify secret detection and redaction.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from collector.pipeline.redactor import redact_event, contains_secret


def test_password_field_dropped():
    """Fields named 'password' must be dropped."""
    event = {"metric_value": 42.0, "password": "hunter2"}
    result = redact_event(event)
    assert "password" not in result


def test_raw_prefix_fields_dropped():
    """Fields prefixed with '_raw' must be dropped."""
    event = {
        "metric_value": 42.0,
        "_raw_usernames": ["root", "admin"],
        "_raw_log_line": "auth failure",
    }
    result = redact_event(event)
    assert "_raw_usernames" not in result
    assert "_raw_log_line" not in result
    assert "metric_value" in result


def test_password_pattern_in_string_redacted():
    """String values containing 'password=...' must be redacted."""
    event = {"raw_config_snippet": "password=SuperSecret123"}
    result = redact_event(event)
    # Either dropped or redacted — should not contain the original secret
    if "raw_config_snippet" in result:
        assert "SuperSecret123" not in result.get("raw_config_snippet", "")


def test_bearer_token_in_string_redacted():
    """Bearer tokens in string values must be redacted."""
    assert contains_secret("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.test")


def test_normal_values_pass_through():
    """Normal metric values must pass through unchanged."""
    event = {
        "metric_value": 45.0,
        "metric_category": "cpu",
        "source_id": "src-001",
    }
    result = redact_event(event)
    assert result["metric_value"] == 45.0
    assert result["metric_category"] == "cpu"
    assert result["source_id"] == "src-001"


def test_hostname_field_dropped():
    """The 'hostname' field (contains real host info) must be dropped."""
    event = {"metric_value": 10.0, "hostname": "prod-web-01.internal.company.com"}
    result = redact_event(event)
    assert "hostname" not in result
