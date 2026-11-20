"""
backend/app/models/transfer_audit.py
Records every approved metadata payload that was sent from a collector to SaaS.

This is what the Privacy Center (Egress Proof panel) displays.
The full raw payload stays on the collector — only the approved JSON preview is stored here.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from ..database import Base


class TransferAudit(Base):
    __tablename__ = "transfer_audit"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    collector_id = Column(String, nullable=False)
    # payload_id == event_id from the ingest payload — UNIQUE prevents duplicates
    payload_id = Column(String, unique=True, nullable=False, index=True)
    utc_timestamp = Column(String, nullable=False)
    # JSON list of field names that were included in this payload
    fields_included = Column(Text, default="[]")
    # Status of this transmission
    status = Column(String, default="delivered")   # pending|delivered|failed
    retry_count = Column(Integer, default=0)
    # Safe JSON preview of the approved payload (no secrets, no raw log)
    payload_preview = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
