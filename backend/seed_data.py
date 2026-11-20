"""
backend/seed_data.py
Inserts realistic synthetic seed data for development and demonstrations.

Run once after initializing the database:
    python seed_data.py

This creates two tenants, three users, two collectors, and sample metrics.
No real credentials or sensitive records are included.
"""
import sys
import os
import uuid
from datetime import datetime, timezone, timedelta

# Add the parent directory to the path so we can import the app package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, init_db
from app.models.tenant import Tenant
from app.models.user import User
from app.models.collector import Collector
from app.models.monitored_source import MonitoredSource
from app.models.telemetry import TelemetryEvent, Metric
from app.models.alert import Alert
from app.models.incident import Incident, IncidentAlert
from app.models.notification import Notification
from app.models.transfer_audit import TransferAudit
from app.models.aiops_baseline import AIOpsBaseline
from app.security.auth import hash_password


def seed():
    from app.config import get_settings
    if get_settings().app_env == "production":
        raise RuntimeError("Demo seeding is disabled in production")
    init_db()
    db = SessionLocal()

    # Check if already seeded
    if db.query(Tenant).count() > 0:
        print("Database already seeded. Skipping.")
        db.close()
        return

    print("Seeding database...")

    # ── Tenants ───────────────────────────────────────────────
    alpha = Tenant(id="tenant-alpha", name="Company Alpha", region="us-south", data_residency_region="us-south")
    beta = Tenant(id="tenant-beta", name="Company Beta", region="eu-west", data_residency_region="eu-west")
    db.add_all([alpha, beta])
    db.commit()  # Commit tenants before anything else references them

    # ── Users ─────────────────────────────────────────────────
    # Passwords are bcrypt-hashed — plaintext never stored
    admin = User(id=str(uuid.uuid4()), tenant_id="tenant-alpha", email="admin@alpha.local",
                 hashed_password=hash_password("SentinelAdmin2026!"), role="admin")
    operator = User(id=str(uuid.uuid4()), tenant_id="tenant-alpha", email="operator@alpha.local",
                    hashed_password=hash_password("SentinelOp2026!"), role="operator")
    viewer = User(id=str(uuid.uuid4()), tenant_id="tenant-beta", email="viewer@beta.local",
                  hashed_password=hash_password("SentinelView2026!"), role="viewer")
    db.add_all([admin, operator, viewer])
    db.commit()

    # ── Collectors ────────────────────────────────────────────
    # API keys are bcrypt-hashed — the plaintext key is configured in .env
    col_alpha_id = str(uuid.uuid4())
    col_beta_id = str(uuid.uuid4())
    col_alpha = Collector(
        id=col_alpha_id, tenant_id="tenant-alpha",
        name="Alpha-Collector-01",
        api_key_hash=hash_password("collector-secret-key-cicada2026"),
        status="online", region="us-south", version="1.0.0",
        last_heartbeat_at=datetime.now(timezone.utc),
    )
    col_beta = Collector(
        id=col_beta_id, tenant_id="tenant-beta",
        name="Beta-Collector-01",
        api_key_hash=hash_password("collector-secret-key-beta-2026"),
        status="online", region="eu-west", version="1.0.0",
        last_heartbeat_at=datetime.now(timezone.utc),
    )
    db.add_all([col_alpha, col_beta])
    db.commit()

    # ── Monitored Sources ─────────────────────────────────────
    sources = [
        MonitoredSource(id=str(uuid.uuid4()), tenant_id="tenant-alpha", collector_id=col_alpha_id,
                        source_id="src-alpha-01", display_name="Alpha Server 01", source_type="server"),
        MonitoredSource(id=str(uuid.uuid4()), tenant_id="tenant-alpha", collector_id=col_alpha_id,
                        source_id="src-alpha-02", display_name="Alpha Server 02", source_type="server"),
        MonitoredSource(id=str(uuid.uuid4()), tenant_id="tenant-beta", collector_id=col_beta_id,
                        source_id="src-beta-01", display_name="Beta Server 01", source_type="server"),
        MonitoredSource(id=str(uuid.uuid4()), tenant_id="tenant-beta", collector_id=col_beta_id,
                        source_id="src-beta-02", display_name="Beta Application 01", source_type="application"),
    ]
    db.add_all(sources)

    # ── Synthetic Metrics ─────────────────────────────────────
    now = datetime.now(timezone.utc)
    # Build 20 baseline samples so AIOps warmup completes on first run
    for i in range(20):
        t = (now - timedelta(minutes=20-i)).isoformat()
        for src, tid in [("src-alpha-01", "tenant-alpha"), ("src-beta-01", "tenant-beta")]:
            for cat, val in [("cpu", 25.0 + i*0.5), ("memory", 45.0 + i*0.3), ("disk", 60.0), ("network", 10.0)]:
                eid = str(uuid.uuid4())
                db.add(TelemetryEvent(
                    id=str(uuid.uuid4()), tenant_id=tid, source_id=src,
                    event_id=eid, utc_timestamp=t, event_time=t,
                    source_timezone="UTC", metric_category=cat,
                    metric_value=val, severity="info", health_status="excellent",
                    collector_id=col_alpha_id if tid == "tenant-alpha" else col_beta_id,
                ))
                db.add(Metric(
                    id=str(uuid.uuid4()), tenant_id=tid, source_id=src,
                    category=cat, value=val, utc_timestamp=t, event_time=t,
                    data_source="seed",   # Explicitly tagged as synthetic seed data
                ))

    # ── Seed AIOps Baselines ───────────────────────────────────
    # Pre-populate the persistent baseline table so Z-score detection is active
    # immediately after seeding, without waiting for 10 live collector samples.
    import json
    import numpy as np
    for src, tid in [("src-alpha-01", "tenant-alpha"), ("src-beta-01", "tenant-beta")]:
        for cat, typical_val, noise in [("cpu", 27.5, 2.5), ("memory", 48.5, 2.0), ("disk", 60.0, 0.5), ("network", 10.0, 1.0)]:
            samples = [typical_val + (i - 10) * noise * 0.1 for i in range(20)]
            arr = np.array(samples, dtype=float)
            mean = float(np.mean(arr))
            std = float(np.std(arr))
            db.add(AIOpsBaseline(
                source_id=src, category=cat, tenant_id=tid,
                mean=round(mean, 4), std_dev=max(round(std, 4), 0.01),
                sample_count=20,
                samples_json=json.dumps([round(s, 2) for s in samples]),
            ))
    db.commit()

    # ── Sample Alerts ─────────────────────────────────────────
    incident_id = str(uuid.uuid4())
    alert1_id = str(uuid.uuid4())
    alert2_id = str(uuid.uuid4())

    incident = Incident(
        id=incident_id, tenant_id="tenant-alpha",
        title="Possible src-alpha-01 Resource Saturation",
        severity="warning", status="open", source_id="src-alpha-01",
        description="Multiple elevated metrics detected on src-alpha-01.",
    )
    db.add(incident)
    db.flush()  # Flush so incident.id is committed before alerts reference it

    a1 = Alert(id=alert1_id, tenant_id="tenant-alpha", source_id="src-alpha-01",
               alert_type="anomaly", severity="warning",
               message="CPU value of 72.0 is above the recent baseline of 30.0 (±5.0) by 8.4 standard deviations.",
               metric_category="cpu", baseline_value=30.0, observed_value=72.0, deviation=8.4,
               incident_id=incident_id)
    a2 = Alert(id=alert2_id, tenant_id="tenant-alpha", source_id="src-alpha-01",
               alert_type="anomaly", severity="warning",
               message="MEMORY value of 85.0 is above the recent baseline of 46.0 (±3.0) by 13.0 standard deviations.",
               metric_category="memory", baseline_value=46.0, observed_value=85.0, deviation=13.0,
               incident_id=incident_id)
    db.add_all([a1, a2])

    db.add_all([
        IncidentAlert(incident_id=incident_id, alert_id=alert1_id),
        IncidentAlert(incident_id=incident_id, alert_id=alert2_id),
    ])

    # ── Sample Notifications ──────────────────────────────────
    for sev, title, desc in [
        ("warning", "WARNING — src-alpha-01", "CPU usage elevated above baseline."),
        ("info", "INFO — src-alpha-02", "Collector heartbeat received normally."),
        ("critical", "CRITICAL — src-alpha-01", "Memory usage critically elevated."),
    ]:
        db.add(Notification(
            id=str(uuid.uuid4()), tenant_id="tenant-alpha",
            source_id="src-alpha-01", title=title, severity=sev,
            description=desc, utc_timestamp=now.isoformat(), is_read=False,
            incident_id=incident_id if sev != "info" else None,
            recommended_action="Investigate resource usage on src-alpha-01.",
        ))

    # ── Sample Transfer Audit ─────────────────────────────────
    for i in range(3):
        t = (now - timedelta(minutes=i*5)).isoformat()
        eid = str(uuid.uuid4())
        db.add(TransferAudit(
            id=str(uuid.uuid4()), tenant_id="tenant-alpha", collector_id=col_alpha_id,
            payload_id=eid, utc_timestamp=t,
            fields_included='["tenant_id","source_id","event_id","utc_timestamp","event_time","source_timezone","metric_category","metric_value","severity","health_status","alert_context","collector_id"]',
            status="delivered", retry_count=0,
            payload_preview=f'{{"tenant_id":"tenant-alpha","source_id":"src-alpha-01","event_id":"{eid}","utc_timestamp":"{t}","event_time":"{t}","source_timezone":"UTC","metric_category":"cpu","metric_value":{25.0+i*5},"severity":"info","health_status":"excellent","alert_context":"","collector_id":"{col_alpha_id}"}}',
        ))

    db.commit()
    db.close()
    print("[OK] Database seeded successfully!")
    print("  Admin:    admin@alpha.local / SentinelAdmin2026!")
    print("  Operator: operator@alpha.local / SentinelOp2026!")
    print("  Viewer:   viewer@beta.local / SentinelView2026!")


if __name__ == "__main__":
    seed()
