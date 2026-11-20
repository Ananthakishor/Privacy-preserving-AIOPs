"""backend/app/models/incident.py — Correlated incident grouping related alerts."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, PrimaryKeyConstraint
from ..database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    severity = Column(String, nullable=False)            # info|warning|critical
    # Status lifecycle: open → acknowledged → resolved
    status = Column(String, default="open")
    source_id = Column(String, nullable=False, index=True)
    description = Column(String, default="")
    health_state_before = Column(String, nullable=True)
    health_state_after = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)


class IncidentAlert(Base):
    """Junction table linking alerts to their parent incident."""
    __tablename__ = "incident_alerts"

    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    alert_id = Column(String, ForeignKey("alerts.id"), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("incident_id", "alert_id"),
    )
