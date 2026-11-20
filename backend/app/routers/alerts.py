"""backend/app/routers/alerts.py"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from ..database import get_db
from ..models.alert import Alert
from ..schemas.alert import AlertResponse, AlertAcknowledge
from ..security.dependencies import get_current_user, require_role
from ..services.audit_service import log_audit

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


@router.get("/", response_model=List[AlertResponse])
def list_alerts(
    severity: Optional[str] = None,
    source_id: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = 100,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Alert).filter(Alert.tenant_id == current_user.tenant_id)
    if severity:
        query = query.filter(Alert.severity == severity)
    if source_id:
        query = query.filter(Alert.source_id == source_id)
    if acknowledged is not None:
        query = query.filter(Alert.is_acknowledged == acknowledged)
    alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()
    return [AlertResponse(
        id=a.id, tenant_id=a.tenant_id, source_id=a.source_id,
        alert_type=a.alert_type, severity=a.severity, message=a.message,
        metric_category=a.metric_category, baseline_value=a.baseline_value,
        observed_value=a.observed_value, deviation=a.deviation,
        is_acknowledged=a.is_acknowledged, incident_id=a.incident_id,
        created_at=a.created_at.isoformat(),
    ) for a in alerts]


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.query(Alert).filter(Alert.id == alert_id, Alert.tenant_id == current_user.tenant_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse(
        id=a.id, tenant_id=a.tenant_id, source_id=a.source_id,
        alert_type=a.alert_type, severity=a.severity, message=a.message,
        metric_category=a.metric_category, baseline_value=a.baseline_value,
        observed_value=a.observed_value, deviation=a.deviation,
        is_acknowledged=a.is_acknowledged, incident_id=a.incident_id,
        created_at=a.created_at.isoformat(),
    )


@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: str,
    body: AlertAcknowledge,
    current_user=Depends(require_role("admin", "operator")),
    db: Session = Depends(get_db),
):
    a = db.query(Alert).filter(Alert.id == alert_id, Alert.tenant_id == current_user.tenant_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    a.is_acknowledged = True
    a.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    log_audit("alert_acknowledged", current_user.id, current_user.tenant_id, {"alert_id": alert_id})
    return {"status": "acknowledged"}
