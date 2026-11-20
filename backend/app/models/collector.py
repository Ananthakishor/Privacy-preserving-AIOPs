"""backend/app/models/collector.py — Local collector registration and status."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey
from ..database import Base


class Collector(Base):
    __tablename__ = "collectors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    # Store bcrypt hash of the API key — never the plaintext key
    api_key_hash = Column(String, nullable=False)
    # Status: online | offline | unknown
    status = Column(String, default="unknown")
    region = Column(String, default="us-south")
    version = Column(String, default="1.0.0")
    last_heartbeat_at = Column(DateTime, nullable=True)
    buffered_count = Column(Integer, default=0)
    cpu_pct = Column(Float, default=0.0)
    mem_pct = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
