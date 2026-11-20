"""
backend/app/aiops/correlator.py
Groups related alerts into a single incident to reduce alert fatigue.

Correlation rules (must satisfy ALL):
1. Same source_id — different servers have independent problems
2. Within a 5-minute time window — concurrent events are likely related
3. At least 2 alerts — a single alert does not form an incident alone

This prevents unrelated events from being merged just because they happened
at the same time (e.g. CPU spike on server-A and disk issue on server-B
are NOT correlated even if simultaneous).
"""
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from ..models.alert import Alert
from ..models.incident import Incident, IncidentAlert

CORRELATION_WINDOW_MINUTES = 5


def correlate_alerts(db: Session, tenant_id: str, new_alert: Alert) -> Optional[Incident]:
    """
    Try to correlate a new alert with existing open alerts on the same source.

    If 2+ unacknowledged alerts from the same source_id exist within the
    correlation window, group them into one incident (or add to an existing one).

    Returns the Incident if correlation happened, None if the alert stands alone.
    """
    window_start = datetime.now(timezone.utc) - timedelta(minutes=CORRELATION_WINDOW_MINUTES)

    # Find recent unacknowledged alerts for the same source (excluding the new one)
    related_alerts = db.query(Alert).filter(
        Alert.tenant_id == tenant_id,
        Alert.source_id == new_alert.source_id,
        Alert.id != new_alert.id,
        Alert.is_acknowledged == False,
        Alert.created_at >= window_start,
    ).all()

    if not related_alerts:
        return None  # Lone alert — no correlation yet

    # Check if there is already an open incident for this source
    existing_incident = db.query(Incident).filter(
        Incident.tenant_id == tenant_id,
        Incident.source_id == new_alert.source_id,
        Incident.status.in_(["open", "acknowledged"]),
    ).first()

    if existing_incident:
        # Add this alert to the existing incident
        link = IncidentAlert(
            incident_id=existing_incident.id,
            alert_id=new_alert.id,
        )
        db.add(link)
        new_alert.incident_id = existing_incident.id

        # Escalate severity if the new alert is more severe
        severity_rank = {"info": 0, "warning": 1, "critical": 2}
        if severity_rank.get(new_alert.severity, 0) > severity_rank.get(existing_incident.severity, 0):
            existing_incident.severity = new_alert.severity

        db.commit()
        return existing_incident

    # No existing incident — create a new correlated one
    categories = list(set(a.metric_category for a in related_alerts + [new_alert] if a.metric_category))
    title = f"Possible {new_alert.source_id} Resource Issue ({', '.join(categories)})"

    incident = Incident(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        title=title,
        severity=new_alert.severity,
        status="open",
        source_id=new_alert.source_id,
        description=f"Multiple related alerts detected on {new_alert.source_id}. "
                    f"Affected metrics: {', '.join(categories)}.",
    )
    db.add(incident)
    db.flush()  # Get the incident.id before creating links

    # Link all related alerts to this incident
    for alert in related_alerts + [new_alert]:
        link = IncidentAlert(incident_id=incident.id, alert_id=alert.id)
        db.add(link)
        alert.incident_id = incident.id

    db.commit()
    db.refresh(incident)
    return incident
