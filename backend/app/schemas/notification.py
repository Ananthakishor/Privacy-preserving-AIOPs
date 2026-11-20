"""backend/app/schemas/notification.py"""
from pydantic import BaseModel
from typing import Optional


class NotificationResponse(BaseModel):
    id: str
    tenant_id: str
    source_id: str
    title: str
    severity: str
    description: str
    utc_timestamp: str
    is_read: bool
    incident_id: Optional[str] = None
    recommended_action: str
    created_at: str

    class Config:
        from_attributes = True


class NotificationFilter(BaseModel):
    severity: Optional[str] = None
    source_id: Optional[str] = None
    is_read: Optional[bool] = None
