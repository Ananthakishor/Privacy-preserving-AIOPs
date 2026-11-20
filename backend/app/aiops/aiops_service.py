"""
backend/app/aiops/aiops_service.py
Orchestrates the AIOps pipeline after each telemetry ingestion.

Pipeline:
1. Run anomaly detection on the new metric value
2. If anomaly detected → try to correlate with other recent alerts
3. If new incident created → generate explainable recommendation
4. Create user notification for new alerts/incidents
"""
from sqlalchemy.orm import Session
from .anomaly_detector import check_anomaly
from .correlator import correlate_alerts
from .recommender import generate_recommendation
from ..services import notification_service


def process_telemetry(
    db: Session,
    tenant_id: str,
    source_id: str,
    category: str,
    value: float,
    collector_id: str = None,
):
    """
    Run the full AIOps pipeline for a single incoming metric value.
    Called from the telemetry ingest endpoint after storing the event.
    """
    # Step 1: Check for statistical anomaly
    alert = check_anomaly(db, tenant_id, source_id, category, value)
    if alert is None:
        return  # No anomaly detected

    # Step 2: Try to correlate with other recent alerts
    incident = correlate_alerts(db, tenant_id, alert)

    # Step 3: Generate recommendation if a new incident was created
    if incident and incident.status == "open":
        # Only generate recommendation for newly created incidents
        from ..models.recommendation import Recommendation
        existing_rec = db.query(Recommendation).filter(
            Recommendation.incident_id == incident.id
        ).first()
        if not existing_rec:
            generate_recommendation(db, incident)

    # Step 4: Create notification
    if incident:
        dedup_key = f"incident-{incident.id}-{alert.metric_category}"
        notification_service.create_notification(
            db=db,
            tenant_id=tenant_id,
            source_id=source_id,
            title=f"{alert.severity.upper()} — {source_id}",
            severity=alert.severity,
            description=alert.message,
            recommended_action=incident.description,
            incident_id=incident.id,
            dedup_key=dedup_key,
        )
    else:
        # Standalone alert notification
        dedup_key = f"alert-{alert.id}"
        notification_service.create_notification(
            db=db,
            tenant_id=tenant_id,
            source_id=source_id,
            title=f"{alert.severity.upper()} — {source_id}",
            severity=alert.severity,
            description=alert.message,
            recommended_action="Investigate the affected metric and check recent changes.",
            dedup_key=dedup_key,
        )
