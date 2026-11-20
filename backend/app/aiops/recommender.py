"""
backend/app/aiops/recommender.py
Generates explainable, evidence-based recommendations for incidents.

IMPORTANT: Recommendations are grounded in actual observed metadata values.
No confidence percentages are fabricated. The confidence_basis field documents
exactly how any score was derived.
"""
import uuid
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from ..models.alert import Alert
from ..models.incident import Incident, IncidentAlert
from ..models.recommendation import Recommendation

# Rule-based recommendation templates keyed by metric category
_TEMPLATES = {
    "cpu": {
        "title": "Elevated CPU Utilization",
        "steps": [
            "Review currently running processes for unexpected resource consumption",
            "Check for recently deployed applications or configuration changes",
            "Examine scheduled tasks or batch jobs that may have triggered",
            "Verify whether the increased load is expected (e.g. backup, indexing)",
        ],
    },
    "memory": {
        "title": "Memory Pressure Detected",
        "steps": [
            "Identify processes with highest memory consumption",
            "Check for memory leaks in recently deployed services",
            "Review application logs for out-of-memory warnings",
            "Consider restarting non-critical services if memory is not released",
        ],
    },
    "disk": {
        "title": "Disk Utilization Warning",
        "steps": [
            "Identify large files or directories consuming unexpected space",
            "Review log rotation policies — logs may be accumulating",
            "Check for core dumps or temporary files from crashed processes",
            "Plan disk expansion or data archival if trend continues",
        ],
    },
    "network": {
        "title": "Network Performance Degradation",
        "steps": [
            "Check network interface error counters and dropped packets",
            "Review bandwidth utilization per application or service",
            "Verify DNS resolution and upstream connectivity",
            "Check for misconfigured firewall rules or routing changes",
        ],
    },
    "security": {
        "title": "Security Signal Detected",
        "steps": [
            "Review authentication logs for the affected source",
            "Check for unusual process executions or privilege escalations",
            "Verify that security patches are current",
            "Isolate the affected system if compromise is suspected",
        ],
    },
}


def generate_recommendation(db: Session, incident: Incident) -> Recommendation:
    """
    Generate an explainable recommendation for an incident.

    Uses actual alert metadata (observed values, baselines, deviations) as evidence.
    Returns the persisted Recommendation record.
    """
    # Collect all alerts linked to this incident
    links = db.query(IncidentAlert).filter(
        IncidentAlert.incident_id == incident.id
    ).all()
    alert_ids = [l.alert_id for l in links]
    alerts = db.query(Alert).filter(Alert.id.in_(alert_ids)).all()

    # Build contributing signals from actual alert data
    contributing_signals = []
    categories = []
    for alert in alerts:
        signal = {
            "signal": f"{alert.metric_category} anomaly on {alert.source_id}",
            "observed_value": alert.observed_value,
            "baseline": alert.baseline_value,
            "deviation": alert.deviation,
        }
        contributing_signals.append(signal)
        if alert.metric_category and alert.metric_category not in categories:
            categories.append(alert.metric_category)

    # Pick the dominant category for template selection
    primary_category = categories[0] if categories else "cpu"
    template = _TEMPLATES.get(primary_category, _TEMPLATES["cpu"])

    # Build explanation referencing real values
    if contributing_signals:
        signal_summary = "; ".join(
            f"{s['signal']} (observed: {s['observed_value']}, baseline: {s['baseline']}, "
            f"{s['deviation']:.1f}σ deviation)"
            for s in contributing_signals if s['observed_value'] is not None
        )
        explanation = (
            f"Incident on {incident.source_id} involves {len(alerts)} related alert(s). "
            f"Detected signals: {signal_summary}. "
            f"These signals are statistically significant deviations from recent baselines."
        )
    else:
        explanation = f"Incident on {incident.source_id}: {incident.description}"

    rec = Recommendation(
        id=str(uuid.uuid4()),
        tenant_id=incident.tenant_id,
        incident_id=incident.id,
        explanation=explanation,
        contributing_signals=json.dumps(contributing_signals),
        suggested_steps=json.dumps(template["steps"]),
        confidence_basis="rule-based: Z-score threshold (>2.5σ) and multi-signal correlation",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec
