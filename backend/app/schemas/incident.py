"""backend/app/schemas/incident.py"""
from pydantic import BaseModel
from typing import Optional, List


class IncidentResponse(BaseModel):
    id: str
    tenant_id: str
    title: str
    severity: str
    status: str
    source_id: str
    description: str
    health_state_before: Optional[str] = None
    health_state_after: Optional[str] = None
    created_at: str
    resolved_at: Optional[str] = None

    class Config:
        from_attributes = True


class IncidentResolve(BaseModel):
    resolution_note: str = ""


class IncidentTimelineEvent(BaseModel):
    timestamp: str
    event_type: str   # created|alert_added|acknowledged|severity_changed|resolved
    description: str
    actor: Optional[str] = None
