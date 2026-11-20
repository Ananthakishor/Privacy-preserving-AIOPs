"""backend/app/schemas/alert.py"""
from pydantic import BaseModel
from typing import Optional


class AlertResponse(BaseModel):
    id: str
    tenant_id: str
    source_id: str
    alert_type: str
    severity: str
    message: str
    metric_category: Optional[str] = None
    baseline_value: Optional[float] = None
    observed_value: Optional[float] = None
    deviation: Optional[float] = None
    is_acknowledged: bool
    incident_id: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class AlertAcknowledge(BaseModel):
    acknowledged_by: str  # user_id
