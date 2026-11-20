"""backend/app/schemas/aiops.py"""
from pydantic import BaseModel
from typing import List, Optional


class AnomalyResult(BaseModel):
    alert_id: str
    source_id: str
    metric_category: str
    observed_value: float
    expected_baseline: float
    deviation_sigma: float
    severity: str
    explanation: str
    detected_at: str


class ContributingSignal(BaseModel):
    signal: str
    observed_value: float
    baseline: float
    deviation: float


class RecommendationResponse(BaseModel):
    id: str
    incident_id: str
    explanation: str
    contributing_signals: List[ContributingSignal]
    suggested_steps: List[str]
    confidence_basis: str
    created_at: str

    class Config:
        from_attributes = True
