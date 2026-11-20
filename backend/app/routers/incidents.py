"""backend/app/routers/incidents.py"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from ..database import get_db
from ..models.incident import Incident, IncidentAlert
from ..models.alert import Alert
from ..schemas.incident import IncidentResponse, IncidentResolve, IncidentTimelineEvent
from ..security.dependencies import get_current_user, require_role
from ..services.audit_service import log_audit

router = APIRouter(prefix="/api/v1/incidents", tags=["Incidents"])


@router.get("/", response_model=List[IncidentResponse])
def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Incident).filter(Incident.tenant_id == current_user.tenant_id)
    if status:
        query = query.filter(Incident.status == status)
    if severity:
        query = query.filter(Incident.severity == severity)
    incidents = query.order_by(Incident.created_at.desc()).limit(limit).all()
    return [_to_response(i) for i in incidents]


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(incident_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    i = db.query(Incident).filter(Incident.id == incident_id, Incident.tenant_id == current_user.tenant_id).first()
    if not i:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _to_response(i)


@router.post("/{incident_id}/resolve")
def resolve_incident(
    incident_id: str,
    body: IncidentResolve,
    current_user=Depends(require_role("admin", "operator")),
    db: Session = Depends(get_db),
):
    i = db.query(Incident).filter(Incident.id == incident_id, Incident.tenant_id == current_user.tenant_id).first()
    if not i:
        raise HTTPException(status_code=404, detail="Incident not found")
    i.status = "resolved"
    i.resolved_at = datetime.now(timezone.utc)
    db.commit()
    log_audit("incident_resolved", current_user.id, current_user.tenant_id,
              {"incident_id": incident_id, "note": body.resolution_note})
    return {"status": "resolved"}


@router.post("/{incident_id}/acknowledge")
def acknowledge_incident(
    incident_id: str,
    current_user=Depends(require_role("admin", "operator")),
    db: Session = Depends(get_db),
):
    i = db.query(Incident).filter(Incident.id == incident_id, Incident.tenant_id == current_user.tenant_id).first()
    if not i:
        raise HTTPException(status_code=404, detail="Incident not found")
    i.status = "acknowledged"
    db.commit()
    log_audit("incident_acknowledged", current_user.id, current_user.tenant_id, {"incident_id": incident_id})
    return {"status": "acknowledged"}


@router.get("/{incident_id}/timeline", response_model=List[IncidentTimelineEvent])
def get_timeline(incident_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    i = db.query(Incident).filter(Incident.id == incident_id, Incident.tenant_id == current_user.tenant_id).first()
    if not i:
        raise HTTPException(status_code=404, detail="Incident not found")

    timeline = []
    # Created
    timeline.append(IncidentTimelineEvent(
        timestamp=i.created_at.isoformat(),
        event_type="created",
        description=f"Incident created: {i.title}",
    ))
    # Related alerts
    links = db.query(IncidentAlert).filter(IncidentAlert.incident_id == incident_id).all()
    for link in links:
        alert = db.query(Alert).filter(Alert.id == link.alert_id).first()
        if alert:
            timeline.append(IncidentTimelineEvent(
                timestamp=alert.created_at.isoformat(),
                event_type="alert_added",
                description=f"Alert added: {alert.message[:100]}",
            ))
    # Resolution
    if i.resolved_at:
        timeline.append(IncidentTimelineEvent(
            timestamp=i.resolved_at.isoformat(),
            event_type="resolved",
            description="Incident resolved",
        ))

    timeline.sort(key=lambda x: x.timestamp)
    return timeline


def _to_response(i: Incident) -> IncidentResponse:
    return IncidentResponse(
        id=i.id, tenant_id=i.tenant_id, title=i.title, severity=i.severity,
        status=i.status, source_id=i.source_id, description=i.description,
        health_state_before=i.health_state_before, health_state_after=i.health_state_after,
        created_at=i.created_at.isoformat(),
        resolved_at=i.resolved_at.isoformat() if i.resolved_at else None,
    )
