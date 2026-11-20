"""
backend/app/routers/telemetry.py
Secure metadata ingestion endpoint.

This is the trust boundary: only allow-listed fields are accepted.
Pydantic schema validation rejects any payload that includes extra fields
or violates field constraints. HTTP 409 is returned for duplicate event_ids.
"""
import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.telemetry import TelemetryEvent, Metric
from ..models.transfer_audit import TransferAudit
from ..models.collector import Collector
from ..schemas.telemetry import TelemetryIngestPayload, MetricResponse
from ..security.dependencies import get_current_user, get_collector_from_api_key
from ..aiops.aiops_service import process_telemetry

router = APIRouter(prefix="/api/v1/telemetry", tags=["Telemetry"])


@router.post("/ingest", status_code=201)
def ingest(
    payload: TelemetryIngestPayload,
    collector: Collector = Depends(get_collector_from_api_key),
    db: Session = Depends(get_db),
):
    """
    Accept an approved metadata payload from a collector.

    - Schema validation enforces the allow-list (extra fields rejected with 422)
    - Duplicate event_id returns HTTP 409 (idempotent delivery)
    - Triggers AIOps pipeline after storing
    - Writes a transfer_audit record for the Privacy Center
    """
    # Idempotency check — reject duplicate event_ids
    existing = db.query(TelemetryEvent).filter(
        TelemetryEvent.event_id == payload.event_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate event_id: {payload.event_id} already received"
        )

    # Store the allow-listed telemetry event
    event = TelemetryEvent(
        id=str(uuid.uuid4()),
        tenant_id=payload.tenant_id,
        source_id=payload.source_id,
        event_id=payload.event_id,
        utc_timestamp=payload.utc_timestamp,
        event_time=payload.event_time,
        source_timezone=payload.source_timezone,
        metric_category=payload.metric_category,
        metric_value=payload.metric_value,
        severity=payload.severity,
        health_status=payload.health_status,
        alert_context=payload.alert_context[:200],  # hard cap
        collector_id=payload.collector_id,
    )
    db.add(event)

    # Also store in metrics table for time-series queries
    metric = Metric(
        id=str(uuid.uuid4()),
        tenant_id=payload.tenant_id,
        source_id=payload.source_id,
        category=payload.metric_category,
        value=payload.metric_value,
        utc_timestamp=payload.utc_timestamp,
        event_time=payload.event_time,
        data_source=payload.data_source,
    )
    db.add(metric)

    # Write transfer audit record for Privacy Center
    allowed_fields = list(TelemetryIngestPayload.model_fields.keys())
    audit = TransferAudit(
        id=str(uuid.uuid4()),
        tenant_id=payload.tenant_id,
        collector_id=payload.collector_id,
        payload_id=payload.event_id,
        utc_timestamp=payload.utc_timestamp,
        fields_included=json.dumps(allowed_fields),
        status="delivered",
        retry_count=0,
        payload_preview=json.dumps(payload.model_dump()),
    )
    db.add(audit)
    db.commit()

    # Run AIOps pipeline asynchronously (anomaly detection + correlation)
    try:
        process_telemetry(
            db=db,
            tenant_id=payload.tenant_id,
            source_id=payload.source_id,
            category=payload.metric_category,
            value=payload.metric_value,
            collector_id=payload.collector_id,
        )
    except Exception as e:
        # AIOps failure should not break ingestion
        pass

    return {"status": "accepted", "event_id": payload.event_id}


@router.get("/metrics", response_model=List[MetricResponse])
def get_metrics(
    source_id: Optional[str] = None,
    category: Optional[str] = None,
    minutes: int = 60,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Query recent metrics for the authenticated tenant."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    cutoff_str = cutoff.isoformat()

    query = db.query(Metric).filter(
        Metric.tenant_id == current_user.tenant_id,
        Metric.event_time >= cutoff_str,
    )
    if source_id:
        query = query.filter(Metric.source_id == source_id)
    if category:
        query = query.filter(Metric.category == category)

    metrics = query.order_by(Metric.event_time.asc()).limit(500).all()
    return [MetricResponse(
        id=m.id, source_id=m.source_id, category=m.category,
        value=m.value, utc_timestamp=m.utc_timestamp, event_time=m.event_time,
        data_source=m.data_source or "live",
    ) for m in metrics]


@router.get("/history")
def get_history(
    source_id: Optional[str] = None,
    category: Optional[str] = None,
    hours: int = 24,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get historical metric data grouped by hour for trend charts."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_str = cutoff.isoformat()

    query = db.query(Metric).filter(
        Metric.tenant_id == current_user.tenant_id,
        Metric.event_time >= cutoff_str,
    )
    if source_id:
        query = query.filter(Metric.source_id == source_id)
    if category:
        query = query.filter(Metric.category == category)

    metrics = query.order_by(Metric.event_time.asc()).all()
    return [{"source_id": m.source_id, "category": m.category,
             "value": m.value, "event_time": m.event_time} for m in metrics]
