"""Provision the first cloud tenant on an empty database, without demo data."""
import os

from sqlalchemy import text

from .config import get_settings
from .database import init_db, SessionLocal
from .models.collector import Collector
from .models.monitored_source import MonitoredSource
from .models.tenant import Tenant
from .models.user import User
from .security.auth import hash_password


def bootstrap():
    if get_settings().app_env != "production":
        raise RuntimeError("Cloud bootstrap requires APP_ENV=production")
    init_db()
    tenant_id = "tenant-tesseract"
    collector_id = "collector-tesseract-01"
    with SessionLocal.begin() as db:
        db.execute(text("SELECT pg_advisory_xact_lock(661902602)"))
        if db.get(Tenant, "tenant-alpha") or db.get(Tenant, "tenant-beta"):
            raise RuntimeError("Select a separate cloud database without the demo tenants")
        if db.get(Tenant, tenant_id):
            admin = db.query(User.id).filter_by(tenant_id=tenant_id, role="admin", is_active=True).first()
            collector = db.query(Collector.id).filter_by(id=collector_id, tenant_id=tenant_id).first()
            if not admin or not collector:
                raise RuntimeError("Existing tenant requires administrator review")
            return
        if db.query(Tenant.id).first():
            raise RuntimeError("First-time setup requires an empty tenant directory")
        email = os.environ.get("INITIAL_ADMIN_EMAIL", "").strip()
        password = os.environ.get("INITIAL_ADMIN_PASSWORD", "")
        key = os.environ.get("INITIAL_COLLECTOR_KEY", "")
        if "@" not in email or email.endswith(".local") or not 24 <= len(password.encode()) <= 72:
            raise RuntimeError("Set the administrator email and a generated 24–72 byte password")
        if not 32 <= len(key.encode()) <= 72 or key == password:
            raise RuntimeError("Set an independent generated 32–72 byte collector key")

        db.add(Tenant(id=tenant_id, name="Tesseract"))
        db.flush()
        db.add(User(tenant_id=tenant_id, email=email, hashed_password=hash_password(password), role="admin"))
        db.add(Collector(id=collector_id, tenant_id=tenant_id, name="Local collector",
                         status="unknown", api_key_hash=hash_password(key)))
        db.flush()
        db.add(MonitoredSource(tenant_id=tenant_id, collector_id=collector_id,
                               source_id="src-tesseract-01", display_name="Monitored host"))


if __name__ == "__main__":
    bootstrap()
