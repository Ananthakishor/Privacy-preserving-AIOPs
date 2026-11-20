"""backend/app/models/tenant.py — Tenant (customer) model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from ..database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    region = Column(String, nullable=False, default="us-south")
    data_residency_region = Column(String, nullable=False, default="us-south")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
