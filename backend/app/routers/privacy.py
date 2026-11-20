"""backend/app/routers/privacy.py — Egress Proof / Privacy Center endpoints."""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models.transfer_audit import TransferAudit
from ..security.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/privacy", tags=["Privacy Center"])


@router.get("/transfer-audit")
def list_transfer_audit(
    limit: int = 100,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all transfer audit records for the tenant (approved payloads only)."""
    records = db.query(TransferAudit).filter(
        TransferAudit.tenant_id == current_user.tenant_id
    ).order_by(TransferAudit.created_at.desc()).limit(limit).all()

    result = []
    for r in records:
        try:
            payload_preview = json.loads(r.payload_preview or "{}")
        except Exception:
            payload_preview = {}
        result.append({
            "id": r.id,
            "payload_id": r.payload_id,
            "collector_id": r.collector_id,
            "utc_timestamp": r.utc_timestamp,
            "fields_included": json.loads(r.fields_included or "[]"),
            "status": r.status,
            "retry_count": r.retry_count,
            "created_at": r.created_at.isoformat(),
            "payload_preview": payload_preview,
        })
    return result


@router.get("/payloads/{payload_id}")
def get_payload(
    payload_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the exact approved payload preview for a specific transmission."""
    r = db.query(TransferAudit).filter(
        TransferAudit.payload_id == payload_id,
        TransferAudit.tenant_id == current_user.tenant_id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Payload not found")
    try:
        payload_data = json.loads(r.payload_preview or "{}")
    except Exception:
        payload_data = {}
    return {
        "payload_id": r.payload_id,
        "collector_id": r.collector_id,
        "utc_timestamp": r.utc_timestamp,
        "fields_included": json.loads(r.fields_included or "[]"),
        "status": r.status,
        "retry_count": r.retry_count,
        "payload_preview": payload_data,
        "note": "Raw logs and secrets are stored only on the collector — this shows the approved metadata only"
    }
