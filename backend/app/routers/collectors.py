"""backend/app/routers/collectors.py — Collector registration and heartbeat."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.collector import Collector
from ..models.heartbeat import CollectorHeartbeat
from ..schemas.collector import CollectorRegister, CollectorHeartbeatPayload, CollectorResponse
from ..security.auth import hash_password, verify_password
from ..security.dependencies import get_current_user, get_collector_from_api_key
from ..services.audit_service import log_audit
from ..config import get_settings
from typing import List, Optional
from fastapi import Header

settings = get_settings()
router = APIRouter(prefix="/api/v1/collectors", tags=["Collectors"])


@router.post("/register", response_model=dict)
def register_collector(
    payload: CollectorRegister,
    x_collector_api_key: Optional[str] = Header(None),
    tenant_id: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Register a new collector. Returns the assigned collector_id."""
    if not x_collector_api_key or not tenant_id:
        raise HTTPException(status_code=400, detail="X-Collector-API-Key and tenant_id headers required")

    if settings.app_env == "production":
        collector = get_collector_from_api_key(x_collector_api_key, db)
        if collector.tenant_id != tenant_id:
            raise HTTPException(403, "Collector tenant mismatch")
        return {"collector_id": collector.id, "message": "Registration confirmed"}

    collector = Collector(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=payload.name,
        api_key_hash=hash_password(x_collector_api_key),
        status="online",
        region=payload.region,
        version=payload.version,
        last_heartbeat_at=datetime.now(timezone.utc),
    )
    db.add(collector)
    db.commit()
    db.refresh(collector)
    log_audit("collector_registered", "system", tenant_id, {"collector_id": collector.id, "name": payload.name})
    return {"collector_id": collector.id, "message": "Collector registered successfully"}


@router.post("/heartbeat")
def heartbeat(
    payload: CollectorHeartbeatPayload,
    collector: Collector = Depends(get_collector_from_api_key),
    db: Session = Depends(get_db),
):
    """Update collector heartbeat and resource metrics."""
    if payload.tenant_id != collector.tenant_id or (settings.app_env == "production" and payload.collector_id != collector.id):
        raise HTTPException(403, "Collector identity mismatch")
    now = datetime.now(timezone.utc)
    collector.last_heartbeat_at = now
    collector.status = "online"
    collector.buffered_count = payload.buffered_count
    collector.cpu_pct = payload.cpu_pct
    collector.mem_pct = payload.mem_pct
    collector.version = payload.version

    hb = CollectorHeartbeat(
        id=str(uuid.uuid4()),
        collector_id=collector.id,
        tenant_id=collector.tenant_id,
        received_at=now,
        cpu_pct=payload.cpu_pct,
        mem_pct=payload.mem_pct,
        buffered_count=payload.buffered_count,
        version=payload.version,
    )
    db.add(hb)
    db.commit()
    return {"status": "ok", "received_at": now.isoformat()}


@router.get("/", response_model=List[CollectorResponse])
def list_collectors(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all collectors for the authenticated user's tenant."""
    query = db.query(Collector)
    if settings.app_env == "production" or current_user.role != "admin":
        query = query.filter(Collector.tenant_id == current_user.tenant_id)
    collectors = query.all()
    result = []
    for c in collectors:
        result.append(CollectorResponse(
            id=c.id,
            tenant_id=c.tenant_id,
            name=c.name,
            status=c.status,
            region=c.region,
            version=c.version,
            last_heartbeat_at=c.last_heartbeat_at.isoformat() if c.last_heartbeat_at else None,
            buffered_count=c.buffered_count or 0,
            cpu_pct=c.cpu_pct or 0.0,
            mem_pct=c.mem_pct or 0.0,
        ))
    return result


@router.get("/{collector_id}", response_model=CollectorResponse)
def get_collector(
    collector_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single collector by ID."""
    c = db.query(Collector).filter(Collector.id == collector_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Collector not found")
    if (settings.app_env == "production" or current_user.role != "admin") and c.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return CollectorResponse(
        id=c.id, tenant_id=c.tenant_id, name=c.name, status=c.status,
        region=c.region, version=c.version,
        last_heartbeat_at=c.last_heartbeat_at.isoformat() if c.last_heartbeat_at else None,
        buffered_count=c.buffered_count or 0, cpu_pct=c.cpu_pct or 0.0, mem_pct=c.mem_pct or 0.0,
    )
