"""backend/app/routers/reports.py — Analytics and reports endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from ..database import get_db
from ..models.incident import Incident
from ..models.alert import Alert
from ..models.telemetry import Metric
from ..security.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


@router.get("/health-summary")
def health_summary(
    hours: int = 24,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get health state distribution over the last N hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    from ..models.telemetry import TelemetryEvent
    events = db.query(TelemetryEvent).filter(
        TelemetryEvent.tenant_id == current_user.tenant_id,
        TelemetryEvent.created_at >= cutoff,
    ).all()

    distribution = defaultdict(int)
    for e in events:
        distribution[e.health_status] += 1

    return {
        "period_hours": hours,
        "distribution": dict(distribution),
        "total_events": len(events),
    }


@router.get("/incident-trends")
def incident_trends(
    days: int = 7,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get incident frequency grouped by day."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    incidents = db.query(Incident).filter(
        Incident.tenant_id == current_user.tenant_id,
        Incident.created_at >= cutoff,
    ).order_by(Incident.created_at.asc()).all()

    by_day = defaultdict(lambda: {"total": 0, "critical": 0, "warning": 0})
    for i in incidents:
        day = i.created_at.strftime("%Y-%m-%d")
        by_day[day]["total"] += 1
        if i.severity in ("critical", "warning"):
            by_day[day][i.severity] += 1

    return {"trends": [{"date": d, **v} for d, v in sorted(by_day.items())]}


@router.get("/source-summary")
def source_summary(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get alert counts per monitored source."""
    alerts = db.query(Alert).filter(
        Alert.tenant_id == current_user.tenant_id
    ).all()

    by_source = defaultdict(lambda: {"total": 0, "critical": 0, "warning": 0})
    for a in alerts:
        by_source[a.source_id]["total"] += 1
        if a.severity in ("critical", "warning"):
            by_source[a.source_id][a.severity] += 1

    return {"sources": [{"source_id": s, **v} for s, v in by_source.items()]}
