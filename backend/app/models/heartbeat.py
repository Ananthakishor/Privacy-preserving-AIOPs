"""backend/app/models/heartbeat.py — Collector heartbeat ping record."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey
from ..database import Base


class CollectorHeartbeat(Base):
    __tablename__ = "collector_heartbeats"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    collector_id = Column(String, ForeignKey("collectors.id"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    received_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    cpu_pct = Column(Float, default=0.0)
    mem_pct = Column(Float, default=0.0)
    buffered_count = Column(Integer, default=0)
    version = Column(String, default="1.0.0")
