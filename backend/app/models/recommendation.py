"""backend/app/models/recommendation.py — Explainable AIOps recommendation."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from ..database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False, index=True)
    # Human-readable explanation referencing actual observed metric values
    explanation = Column(Text, nullable=False)
    # JSON string: list of {signal, value, baseline, deviation} dicts
    contributing_signals = Column(Text, default="[]")
    # JSON string: list of investigation steps
    suggested_steps = Column(Text, default="[]")
    # Documents how any confidence estimate was calculated (no fabrication)
    confidence_basis = Column(String, default="rule-based: threshold and deviation analysis")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
