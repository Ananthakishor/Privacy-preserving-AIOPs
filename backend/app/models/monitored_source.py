"""backend/app/models/monitored_source.py — Server/device being monitored."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from ..database import Base


class MonitoredSource(Base):
    __tablename__ = "monitored_sources"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    collector_id = Column(String, ForeignKey("collectors.id"), nullable=True)
    # Pseudonymous identifier — never store actual hostname with PII
    source_id = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    source_type = Column(String, default="server")  # server | network | application
    region = Column(String, default="us-south")
    timezone = Column(String, default="UTC")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
