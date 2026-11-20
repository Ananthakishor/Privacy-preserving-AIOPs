"""
tests/test_egress_payload.py
Test 8: Egress proof — verify that sensitive fields never reach the backend.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import uuid
from datetime import datetime, timezone


def test_egress_payload_contains_no_secrets(client):
    """After ingest, transfer_audit record must not contain sensitive fields."""
    eid = str(uuid.uuid4())
    headers = {"X-Collector-API-Key": "collector-secret-key-cicada2026"}
    payload = {
        "tenant_id": "tenant-alpha",
        "source_id": "src-alpha-01",
        "event_id": eid,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "event_time": datetime.now(timezone.utc).isoformat(),
        "source_timezone": "UTC",
        "metric_category": "cpu",
        "metric_value": 42.0,
        "severity": "info",
        "health_status": "excellent",
        "alert_context": "normal cpu reading",
        "collector_id": "test-collector",
    }
    r = client.post("/api/v1/telemetry/ingest", json=payload, headers=headers)
    assert r.status_code == 201

    # Retrieve the transfer audit record
    r2 = client.post("/api/v1/auth/login", data={
        "username": "admin@alpha.local", "password": "SentinelAdmin2026!"
    })
    token = r2.json().get("access_token")
    auth = {"Authorization": f"Bearer {token}"}

    r3 = client.get(f"/api/v1/privacy/payloads/{eid}", headers=auth)
    assert r3.status_code == 200
    payload_preview = r3.json().get("payload_preview", {})

    # Verify no raw/sensitive fields in payload_preview
    assert "password" not in str(payload_preview).lower()
    assert "hostname" not in payload_preview
    assert "_raw" not in str(payload_preview)

    # Verify all allowed fields are present
    assert "event_id" in payload_preview
    assert "metric_value" in payload_preview
    assert payload_preview["event_id"] == eid


def test_transfer_audit_exists_after_ingest(client, auth_headers):
    """Every successful ingest must create a transfer_audit record."""
    eid = str(uuid.uuid4())
    headers = {"X-Collector-API-Key": "collector-secret-key-cicada2026"}
    payload = {
        "tenant_id": "tenant-alpha", "source_id": "src-alpha-01",
        "event_id": eid, "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "event_time": datetime.now(timezone.utc).isoformat(), "source_timezone": "UTC",
        "metric_category": "memory", "metric_value": 60.0, "severity": "info",
        "health_status": "excellent", "alert_context": "", "collector_id": "test-col",
    }
    client.post("/api/v1/telemetry/ingest", json=payload, headers=headers)

    r = client.get("/api/v1/privacy/transfer-audit", headers=auth_headers)
    assert r.status_code == 200
    records = r.json()
    matching = [rec for rec in records if rec.get("payload_id") == eid]
    assert len(matching) == 1
    assert matching[0]["status"] == "delivered"
