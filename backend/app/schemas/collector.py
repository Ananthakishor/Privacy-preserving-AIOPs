"""backend/app/schemas/collector.py"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CollectorRegister(BaseModel):
    name: str
    region: str = "us-south"
    version: str = "1.0.0"


class CollectorHeartbeatPayload(BaseModel):
    collector_id: str
    tenant_id: str
    cpu_pct: float = 0.0
    mem_pct: float = 0.0
    buffered_count: int = 0
    version: str = "1.0.0"


class CollectorResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    status: str
    region: str
    version: str
    last_heartbeat_at: Optional[str] = None
    buffered_count: int
    cpu_pct: float
    mem_pct: float

    class Config:
        from_attributes = True
