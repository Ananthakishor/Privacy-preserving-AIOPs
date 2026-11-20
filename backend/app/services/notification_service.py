"""
backend/app/services/notification_service.py
Creates notifications and broadcasts them via WebSocket to connected clients.

Deduplication: If the same incident already has an open (unread) notification
of the same type, a new one is NOT created. This prevents alert fatigue.
"""
import asyncio
import uuid
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..models.notification import Notification


# Global WebSocket manager — set by main.py at startup
# This is a reference to the ConnectionManager instance
_ws_manager = None
_ws_loop = None


def set_ws_manager(manager, loop):
    """Called by main.py to inject the WebSocket manager."""
    global _ws_manager, _ws_loop
    _ws_manager, _ws_loop = manager, loop


def create_notification(
    db: Session,
    tenant_id: str,
    source_id: str,
    title: str,
    severity: str,
    description: str,
    recommended_action: str = "",
    incident_id: str = None,
    dedup_key: str = None,
) -> Notification:
    """
    Create a notification record and broadcast it via WebSocket.

    Deduplication: if dedup_key is provided and an unread notification with
    the same dedup_key already exists for this tenant, skip creating a new one.
    """
    # Check for existing unread notification with same dedup_key
    if dedup_key:
        existing = db.query(Notification).filter(
            Notification.tenant_id == tenant_id,
            Notification.dedup_key == dedup_key,
            Notification.is_read == False
        ).first()
        if existing:
            return existing  # Already notified, don't spam

    notification = Notification(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        source_id=source_id,
        title=title,
        severity=severity,
        description=description,
        utc_timestamp=datetime.now(timezone.utc).isoformat(),
        recommended_action=recommended_action,
        incident_id=incident_id,
        dedup_key=dedup_key,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    # Broadcast to all connected WebSocket clients for this tenant
    if _ws_manager and _ws_loop:
        payload = {
            "type": "notification",
            "data": {
                "id": notification.id,
                "title": notification.title,
                "severity": notification.severity,
                "description": notification.description,
                "source_id": notification.source_id,
                "incident_id": notification.incident_id,
                "utc_timestamp": notification.utc_timestamp,
            }
        }
        asyncio.run_coroutine_threadsafe(
            _ws_manager.broadcast_to_tenant(tenant_id, json.dumps(payload)), _ws_loop
        )

    return notification
