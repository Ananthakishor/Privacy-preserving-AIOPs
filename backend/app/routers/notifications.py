"""backend/app/routers/notifications.py — Notifications + WebSocket push."""
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from ..database import get_db
from ..models.notification import Notification
from ..schemas.notification import NotificationResponse
from ..security.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


@router.get("/", response_model=List[NotificationResponse])
def list_notifications(
    severity: Optional[str] = None,
    source_id: Optional[str] = None,
    is_read: Optional[bool] = None,
    limit: int = 100,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Notification).filter(Notification.tenant_id == current_user.tenant_id)
    if severity:
        query = query.filter(Notification.severity == severity)
    if source_id:
        query = query.filter(Notification.source_id == source_id)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
    return [_to_response(n) for n in notifications]


@router.get("/unread-count")
def unread_count(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    count = db.query(Notification).filter(
        Notification.tenant_id == current_user.tenant_id,
        Notification.is_read == False
    ).count()
    return {"count": count}


@router.post("/{notification_id}/read")
def mark_read(notification_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.tenant_id == current_user.tenant_id
    ).first()
    if n:
        n.is_read = True
        db.commit()
    return {"status": "ok"}


@router.post("/read-all")
def mark_all_read(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(
        Notification.tenant_id == current_user.tenant_id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"status": "ok"}


def _to_response(n: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=n.id, tenant_id=n.tenant_id, source_id=n.source_id,
        title=n.title, severity=n.severity, description=n.description,
        utc_timestamp=n.utc_timestamp, is_read=n.is_read,
        incident_id=n.incident_id, recommended_action=n.recommended_action or "",
        created_at=n.created_at.isoformat(),
    )
