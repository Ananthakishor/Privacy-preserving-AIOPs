"""backend/app/routers/aiops.py — AIOps anomalies and recommendations."""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models.alert import Alert
from ..models.recommendation import Recommendation
from ..schemas.aiops import AnomalyResult, RecommendationResponse, ContributingSignal
from ..security.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/aiops", tags=["AIOps"])


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    source: str
    model: str
    context_used: List[str]
    warning: str = ""


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


@router.post("/ask", response_model=AskResponse)
def ask_ai(
    request: AskRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Ask Sentinel AI a question about the current operational state.

    Uses IBM watsonx AI (Granite model) with ONLY approved metadata as context.
    Raw logs, secrets, and sensitive data are NEVER included in the prompt.
    Falls back to a local rule-based engine if watsonx is unavailable.

    Example questions:
    - "Why is src-alpha-01 unhealthy?"
    - "Which server has the highest CPU usage?"
    - "What incidents occurred recently?"
    - "What is the status of my collectors?"
    """
    if not request.question or len(request.question.strip()) < 3:
        raise HTTPException(status_code=400, detail="Question must be at least 3 characters")
    if len(request.question) > 500:
        raise HTTPException(status_code=400, detail="Question must be 500 characters or fewer")

    from ..services.watsonx_service import ask_sentinel_ai
    result = ask_sentinel_ai(
        db=db,
        tenant_id=current_user.tenant_id,
        question=request.question.strip(),
    )
    return AskResponse(**result)


@router.get("/predictions")
def get_predictions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return predictive warnings for metrics trending toward critical thresholds.

    Uses linear regression over recent data points. All predictions are labeled
    as ESTIMATES and include the confidence basis so operators can judge reliability.
    This endpoint never claims certainty — it only surfaces concerning trends.
    """
    from ..aiops.predictor import predict_threshold_breach
    from ..models.telemetry import Metric
    from sqlalchemy import distinct

    # Get all unique (source_id, category) pairs for this tenant
    pairs = (
        db.query(Metric.source_id, Metric.category)
        .filter(Metric.tenant_id == current_user.tenant_id)
        .distinct()
        .all()
    )

    predictions = []
    for source_id, category in pairs:
        pred = predict_threshold_breach(
            db=db,
            tenant_id=current_user.tenant_id,
            source_id=source_id,
            category=category,
        )
        if pred is not None:
            predictions.append(pred)

    # Sort by minutes_to_breach ascending (most urgent first)
    predictions.sort(key=lambda p: p["minutes_to_breach"])

    return {
        "predictions": predictions,
        "total": len(predictions),
        "note": (
            "These are ESTIMATES based on linear regression. "
            "They indicate concerning trends, not guaranteed outcomes. "
            "Always verify with actual metric data before taking action."
        ),
    }
