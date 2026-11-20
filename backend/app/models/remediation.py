"""backend/app/models/remediation.py — Safe remediation simulator records."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from ..database import Base


class RemediationApproval(Base):
    """An operator proposes a remediation action; it requires approval before simulation."""
    __tablename__ = "remediation_approvals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    proposed_action = Column(String, nullable=False)
    proposed_by = Column(String, nullable=False)         # user_id
    approved_by = Column(String, nullable=True)          # user_id or None
    # Status: pending → approved/rejected → executed
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    approved_at = Column(DateTime, nullable=True)


class RemediationAudit(Base):
    """Immutable record of what happened when an approved action was simulated."""
    __tablename__ = "remediation_audit"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    approval_id = Column(String, ForeignKey("remediation_approvals.id"), nullable=False)
    action_taken = Column(String, nullable=False)
    result = Column(String, nullable=False)              # success|failure|simulated
    audit_log = Column(Text, default="{}")               # JSON details of the simulation
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    rolled_back_at = Column(DateTime, nullable=True)
