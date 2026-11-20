"""backend/app/routers/aiops.py — AIOps anomalies and recommendations."""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models.alert import Alert
from ..models.recommendation import Recommendation
from ..schemas.aiops import AnomalyResult, RecommendationResponse, ContributingSignal
from ..security.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/aiops", tags=["AIOps"])


@router.get("/anomalies", response_model=List[AnomalyResult])
def get_anomalies(
    limit: int = 50,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alerts = db.query(Alert).filter(
        Alert.tenant_id == current_user.tenant_id,
        Alert.alert_type == "anomaly",
    ).order_by(Alert.created_at.desc()).limit(limit).all()

    return [AnomalyResult(
        alert_id=a.id, source_id=a.source_id,
        metric_category=a.metric_category or "",
        observed_value=a.observed_value or 0,
        expected_baseline=a.baseline_value or 0,
        deviation_sigma=a.deviation or 0,
        severity=a.severity, explanation=a.message,
        detected_at=a.created_at.isoformat(),
    ) for a in alerts]


@router.get("/recommendations", response_model=List[RecommendationResponse])
def get_recommendations(
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recs = db.query(Recommendation).filter(
        Recommendation.tenant_id == current_user.tenant_id
    ).order_by(Recommendation.created_at.desc()).limit(limit).all()
    return [_rec_to_response(r) for r in recs]


@router.get("/incidents/{incident_id}/explanation", response_model=RecommendationResponse)
def get_explanation(
    incident_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rec = db.query(Recommendation).filter(
        Recommendation.incident_id == incident_id,
        Recommendation.tenant_id == current_user.tenant_id,
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="No recommendation found for this incident")
    return _rec_to_response(rec)


def _rec_to_response(r: Recommendation) -> RecommendationResponse:
    try:
        signals_raw = json.loads(r.contributing_signals or "[]")
        signals = [ContributingSignal(
            signal=s.get("signal", ""),
            observed_value=s.get("observed_value") or 0,
            baseline=s.get("baseline") or 0,
            deviation=s.get("deviation") or 0,
        ) for s in signals_raw]
    except Exception:
        signals = []
    try:
        steps = json.loads(r.suggested_steps or "[]")
    except Exception:
        steps = []
    return RecommendationResponse(
        id=r.id, incident_id=r.incident_id, explanation=r.explanation,
        contributing_signals=signals, suggested_steps=steps,
        confidence_basis=r.confidence_basis or "",
        created_at=r.created_at.isoformat(),
    )
