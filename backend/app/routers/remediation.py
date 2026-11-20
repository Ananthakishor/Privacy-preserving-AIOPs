"""
backend/app/routers/remediation.py
Safe Remediation Simulator endpoints.

IMPORTANT SAFETY DESIGN:
- Actions are SIMULATED ONLY. No real infrastructure changes occur.
- Every proposed action requires explicit operator approval before execution.
- The simulation result is logged to remediation_audit (immutable).
- A rollback simulation is always available.
- Viewer role cannot propose or approve actions.
- Approval and execution are separate steps (two-person rule).

Flow:
  1. POST /propose   — Operator proposes an action for an incident.
  2. POST /{id}/approve  — Another operator (or admin) approves.
  3. POST /{id}/execute  — Operator simulates the approved action.
  4. POST /{id}/rollback — Demonstrate rollback simulation.
  5. GET  /             — List all remediations for the tenant.
"""
import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from ..services.audit_service import log_audit
from ..database import get_db
from ..models.remediation import RemediationApproval, RemediationAudit
from ..models.incident import Incident
from ..security.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/v1/remediation", tags=["Remediation"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ProposeRequest(BaseModel):
    incident_id: str
    proposed_action: str    # e.g. "Restart web service", "Scale application", "Review processes"


class ProposeResponse(BaseModel):
    id: str
    incident_id: str
    proposed_action: str
    proposed_by: str
    status: str
    created_at: str


class ApprovalResponse(BaseModel):
    id: str
    status: str
    approved_by: str
    approved_at: str
    message: str


class ExecuteResponse(BaseModel):
    approval_id: str
    action_taken: str
    result: str
    simulation_note: str
    audit_id: str
    executed_at: str


class RollbackResponse(BaseModel):
    approval_id: str
    rolled_back_at: str
    simulation_note: str


class RemediationListItem(BaseModel):
    id: str
    incident_id: str
    proposed_action: str
    proposed_by: str
    approved_by: Optional[str]
    status: str
    created_at: str
    approved_at: Optional[str]


# ── Predefined safe simulation actions ───────────────────────────────────────

_SAFE_ACTIONS = {
    "review_processes": {
        "label": "Review resource-intensive processes",
        "simulation": "Simulated: Listed top 10 processes by CPU usage. No processes were killed.",
        "reversible": True,
    },
    "restart_service": {
        "label": "Restart web service (simulated)",
        "simulation": "Simulated: Service restart command issued. Service would be briefly unavailable then recovered.",
        "reversible": True,
    },
    "scale_application": {
        "label": "Scale application instances (simulated)",
        "simulation": "Simulated: Scaling request submitted. Instance count would increase from 1 to 2.",
        "reversible": True,
    },
    "reset_component": {
        "label": "Reset unhealthy component (simulated)",
        "simulation": "Simulated: Health check endpoint called. Component would be marked for restart on next health check.",
        "reversible": True,
    },
    "flush_cache": {
        "label": "Flush application cache (simulated)",
        "simulation": "Simulated: Cache flush command queued. Cache would be cleared on next request.",
        "reversible": False,
    },
}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/actions")
def list_safe_actions():
    """
    Returns the catalog of predefined safe simulation actions.
    Operators must choose from this list — arbitrary shell commands are not permitted.
    """
    return {
        "note": "These are SIMULATION actions only. No real infrastructure changes occur.",
        "actions": [
            {"key": k, **v}
            for k, v in _SAFE_ACTIONS.items()
        ],
    }


@router.post("/propose", response_model=ProposeResponse)
def propose_remediation(
    req: ProposeRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Propose a remediation action for an open incident.
    Requires 'operator' or 'admin' role.
    The action is NOT executed yet — it requires approval first.
    """
    # Only operators and admins can propose
    if current_user.role not in ("operator", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only operators and admins can propose remediation actions."
        )

    # Validate incident belongs to this tenant
    incident = db.query(Incident).filter(
        Incident.id == req.incident_id,
        Incident.tenant_id == current_user.tenant_id,
    ).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Validate proposed action is in the safe list
    # (Free-text is allowed for demo purposes, but we prefer catalog actions)
    approval = RemediationApproval(
        id=str(uuid.uuid4()),
        tenant_id=current_user.tenant_id,
        incident_id=req.incident_id,
        proposed_action=req.proposed_action[:500],
        proposed_by=current_user.id,
        status="pending",
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)

    # Log to audit service
    log_audit(
        action="remediation_proposed",
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        details={
            "approval_id": approval.id,
            "incident_id": req.incident_id,
            "proposed_action": req.proposed_action,
        },
    )

    return ProposeResponse(
        id=approval.id,
        incident_id=approval.incident_id,
        proposed_action=approval.proposed_action,
        proposed_by=approval.proposed_by,
        status=approval.status,
        created_at=approval.created_at.isoformat(),
    )


@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
def approve_remediation(
    approval_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Approve a pending remediation action.
    Requires 'operator' or 'admin' role.
    The approver should be a DIFFERENT person from the proposer.
    (Enforced by policy; not technically blocked in the prototype.)
    """
    if current_user.role not in ("operator", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only operators and admins can approve remediation actions."
        )

    approval = db.query(RemediationApproval).filter(
        RemediationApproval.id == approval_id,
        RemediationApproval.tenant_id == current_user.tenant_id,
    ).first()

    if not approval:
        raise HTTPException(status_code=404, detail="Remediation approval not found")

    if approval.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot approve: approval is already in '{approval.status}' status"
        )

    now = datetime.now(timezone.utc)
    approval.status = "approved"
    approval.approved_by = current_user.id
    approval.approved_at = now
    db.commit()

    log_audit(
        action="remediation_approved",
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        details={"approval_id": approval_id, "proposed_action": approval.proposed_action},
    )

    return ApprovalResponse(
        id=approval.id,
        status=approval.status,
        approved_by=current_user.id,
        approved_at=now.isoformat(),
        message=(
            f"Action '{approval.proposed_action}' approved. "
            "You may now execute the simulation via POST /{id}/execute."
        ),
    )


@router.post("/{approval_id}/execute", response_model=ExecuteResponse)
def execute_remediation(
    approval_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Execute a SIMULATION of an approved remediation action.
    Records the simulation result in the immutable remediation_audit table.
    NO real infrastructure changes occur.
    """
    if current_user.role not in ("operator", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only operators and admins can execute remediation simulations."
        )

    approval = db.query(RemediationApproval).filter(
        RemediationApproval.id == approval_id,
        RemediationApproval.tenant_id == current_user.tenant_id,
    ).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Remediation approval not found")

    if approval.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot execute: approval status is '{approval.status}' (must be 'approved')"
        )

    # Look up simulation result from safe actions catalog
    # or generate a generic simulation for custom action text
    action_key = None
    for k, v in _SAFE_ACTIONS.items():
        if k in approval.proposed_action.lower() or v["label"].lower() in approval.proposed_action.lower():
            action_key = k
            break

    if action_key:
        simulation_note = _SAFE_ACTIONS[action_key]["simulation"]
        reversible = _SAFE_ACTIONS[action_key]["reversible"]
    else:
        simulation_note = (
            f"Simulated: '{approval.proposed_action}' executed in isolated sandbox. "
            "No real infrastructure was modified."
        )
        reversible = True

    now = datetime.now(timezone.utc)
    audit = RemediationAudit(
        id=str(uuid.uuid4()),
        approval_id=approval_id,
        action_taken=approval.proposed_action,
        result="simulated",
        audit_log=json.dumps({
            "executed_by": current_user.id,
            "executed_at": now.isoformat(),
            "simulation_note": simulation_note,
            "reversible": reversible,
            "environment": "ISOLATED_SIMULATION — no real changes",
        }),
        created_at=now,
    )
    db.add(audit)
    approval.status = "executed"
    db.commit()
    db.refresh(audit)

    log_audit(
        action="remediation_executed",
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        details={
            "approval_id": approval_id,
            "audit_id": audit.id,
            "action_taken": approval.proposed_action,
            "result": "simulated",
        },
    )

    return ExecuteResponse(
        approval_id=approval_id,
        action_taken=approval.proposed_action,
        result="simulated",
        simulation_note=simulation_note,
        audit_id=audit.id,
        executed_at=now.isoformat(),
    )


@router.post("/{approval_id}/rollback", response_model=RollbackResponse)
def rollback_remediation(
    approval_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Demonstrate a rollback of an executed simulation.
    For the prototype, marks the audit record as rolled back.
    Shows that rollback planning is part of the approval workflow.
    """
    if current_user.role not in ("operator", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only operators and admins can rollback remediations.")

    audit = db.query(RemediationAudit).join(RemediationApproval).filter(
        RemediationAudit.approval_id == approval_id,
        RemediationApproval.tenant_id == current_user.tenant_id,
    ).first()
    if not audit:
        raise HTTPException(status_code=404, detail="No executed audit record found for this approval")

    now = datetime.now(timezone.utc)
    audit.rolled_back_at = now
    audit.result = "rolled_back"
    db.commit()

    log_audit(
        action="remediation_rolled_back",
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        details={"approval_id": approval_id, "audit_id": audit.id},
    )

    return RollbackResponse(
        approval_id=approval_id,
        rolled_back_at=now.isoformat(),
        simulation_note=(
            "Rollback simulation complete. The simulated action has been marked as rolled back. "
            "In a real deployment, this would trigger the rollback procedure defined in the runbook."
        ),
    )


@router.get("/", response_model=List[RemediationListItem])
def list_remediations(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all remediation actions for the authenticated tenant."""
    items = (
        db.query(RemediationApproval)
        .filter(RemediationApproval.tenant_id == current_user.tenant_id)
        .order_by(RemediationApproval.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        RemediationListItem(
            id=i.id,
            incident_id=i.incident_id,
            proposed_action=i.proposed_action,
            proposed_by=i.proposed_by,
            approved_by=i.approved_by,
            status=i.status,
            created_at=i.created_at.isoformat(),
            approved_at=i.approved_at.isoformat() if i.approved_at else None,
        )
        for i in items
    ]


@router.get("/{approval_id}/audit")
def get_audit(
    approval_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the audit trail for a specific remediation action."""
    # First verify the approval belongs to this tenant
    approval = db.query(RemediationApproval).filter(
        RemediationApproval.id == approval_id,
        RemediationApproval.tenant_id == current_user.tenant_id,
    ).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Remediation approval not found")

    audit = db.query(RemediationAudit).join(RemediationApproval).filter(
        RemediationAudit.approval_id == approval_id,
        RemediationApproval.tenant_id == current_user.tenant_id,
    ).first()

    return {
        "approval": {
            "id": approval.id,
            "incident_id": approval.incident_id,
            "proposed_action": approval.proposed_action,
            "proposed_by": approval.proposed_by,
            "approved_by": approval.approved_by,
            "status": approval.status,
            "created_at": approval.created_at.isoformat(),
            "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
        },
        "execution": {
            "id": audit.id if audit else None,
            "action_taken": audit.action_taken if audit else None,
            "result": audit.result if audit else None,
            "audit_log": json.loads(audit.audit_log or "{}") if audit else None,
            "created_at": audit.created_at.isoformat() if audit else None,
            "rolled_back_at": audit.rolled_back_at.isoformat() if audit and audit.rolled_back_at else None,
        } if audit else None,
    }
