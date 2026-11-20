"""backend/app/models/notification.py — User-facing notification record."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from ..database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    source_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    severity = Column(String, nullable=False)    # info|warning|critical|resolved
    description = Column(String, nullable=False)
    utc_timestamp = Column(String, nullable=False)
    is_read = Column(Boolean, default=False, index=True)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=True)
    recommended_action = Column(String, default="")
    # Deduplication key: incident_id + notification type — prevents spam
    dedup_key = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
