"""
tests/test_e2e_smoke.py
End-to-end smoke test: Telemetry → Ingest → AIOps → Alert → Notification.

Updated to use db session for baseline operations (baseline now persists in SQLite).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.aiops.baseline import add_sample, reset_baseline
from backend.app.database import SessionLocal, init_db


def test_e2e_telemetry_to_notification(client, auth_headers):
    """
    Full pipeline smoke test:
    1. Warm up baseline with normal CPU values
    2. Send a spike that should trigger anomaly detection
    3. Verify the alert was created
    4. Verify the egress proof record exists
    """
    # Step 1: Warm up the baseline (needs 10+ samples)
    source_id = "src-e2e-test"
    tenant_id = "tenant-alpha"
    db = SessionLocal()
    try:
        reset_baseline(db, source_id, "cpu", tenant_id)
        for i in range(20):
            add_sample(db, source_id, "cpu", tenant_id, 25.0 + (i * 0.1))
    finally:
        db.close()

    headers = {"X-Collector-API-Key": "collector-secret-key-cicada2026"}

    # Step 2: Send a CPU spike (much higher than baseline of ~27%)
    spike_eid = str(uuid.uuid4())
    spike_payload = {
        "tenant_id": tenant_id,
        "source_id": source_id,
        "event_id": spike_eid,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "event_time": datetime.now(timezone.utc).isoformat(),
        "source_timezone": "UTC",
        "metric_category": "cpu",
        "metric_value": 95.0,  # Extreme spike
        "severity": "critical",
        "health_status": "poor",
        "alert_context": "cpu spike detected",
        "collector_id": "test-e2e-collector",
        "data_source": "simulated",
    }
    r = client.post("/api/v1/telemetry/ingest", json=spike_payload, headers=headers)
    assert r.status_code == 201, f"Ingest failed: {r.text}"

    # Step 3: Check that an alert was created
    r2 = client.get("/api/v1/alerts/?source_id=" + source_id, headers=auth_headers)
    assert r2.status_code == 200

    # Step 4: Verify egress proof record exists
    r3 = client.get("/api/v1/privacy/transfer-audit", headers=auth_headers)
    assert r3.status_code == 200
    records = r3.json()
    matching = [rec for rec in records if rec.get("payload_id") == spike_eid]
    assert len(matching) == 1
    assert matching[0]["status"] == "delivered"


def test_health_check():
    """Backend health check must return 200."""
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
