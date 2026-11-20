"""
backend/app/main.py
FastAPI application entry point.

Registers all routers, configures CORS, manages WebSocket connections,
runs the collector offline detection background task, and initializes
the database on startup.
"""
import asyncio
import json
import logging
import time
from fastapi import HTTPException
from jose import JWTError
from sqlalchemy import text
from .security.auth import decode_token
from .security.dependencies import get_current_user
from datetime import datetime, timezone, timedelta
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .config import get_settings
from .database import init_db, SessionLocal
from .services import notification_service

settings = get_settings()
production = settings.app_env == "production"
origins = [settings.frontend_origin] if production else [settings.frontend_origin, "http://localhost:5173", "http://localhost:3000"]


class ConnectionManager:
    """
    Manages active WebSocket connections grouped by tenant_id.
    When a notification is created, it is broadcast to all connections
    for the relevant tenant only (enforces tenant isolation in real-time).
    """
    def __init__(self):
        # {tenant_id: [WebSocket, ...]}
        self.connections: Dict[str, List[WebSocket]] = {}

    def connect(self, websocket: WebSocket, tenant_id: str):
        if tenant_id not in self.connections:
            self.connections[tenant_id] = []
        self.connections[tenant_id].append(websocket)

    def disconnect(self, websocket: WebSocket, tenant_id: str):
        if tenant_id in self.connections:
            self.connections[tenant_id] = [
                ws for ws in self.connections[tenant_id] if ws != websocket
            ]

    async def broadcast_to_tenant(self, tenant_id: str, message: str):
        """Send a message to all WebSocket clients for a specific tenant."""
        if tenant_id not in self.connections:
            return
        dead_connections = []
        for ws in self.connections[tenant_id]:
            try:
                await ws.send_text(message)
            except Exception:
                dead_connections.append(ws)
        # Clean up dead connections
        for ws in dead_connections:
            self.disconnect(ws, tenant_id)


manager = ConnectionManager()


async def check_offline_collectors():
    """
    Background task: runs every 10 seconds.
    Marks collectors as offline if they haven't sent a heartbeat
    within COLLECTOR_OFFLINE_THRESHOLD_SECONDS (default: 60 seconds).
    Creates a Poor health notification when a collector goes offline.
    This satisfies the PDF requirement: offline detection within 60 seconds.
    """
    while True:
        db = SessionLocal()
        try:
            from .models.collector import Collector
            threshold = datetime.now(timezone.utc) - timedelta(
                seconds=settings.collector_offline_threshold_seconds
            )
            # Find online collectors that haven't been heard from recently
            stale_collectors = db.query(Collector).filter(
                Collector.status == "online",
                Collector.last_heartbeat_at < threshold,
            ).all()

            for collector in stale_collectors:
                collector.status = "offline"
                db.commit()
                # Create notification for the tenant
                notification_service.create_notification(
                    db=db,
                    tenant_id=collector.tenant_id,
                    source_id=collector.id,
                    title=f"Collector Offline — {collector.name}",
                    severity="critical",
                    description=(
                        f"Collector '{collector.name}' has not sent a heartbeat for "
                        f"more than {settings.collector_offline_threshold_seconds} seconds."
                    ),
                    recommended_action="Check collector host connectivity and process status.",
                    dedup_key=f"collector-offline-{collector.id}",
                )
        except Exception as exc:
            logging.getLogger(__name__).error("Collector status check failed (%s)", type(exc).__name__)
        finally:
            db.close()
        await asyncio.sleep(10)  # Check every 10 seconds


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize DB and start background tasks. Shutdown: clean up."""
    init_db()
    # Inject WebSocket manager into notification service
    notification_service.set_ws_manager(manager, asyncio.get_running_loop())
    # Start collector offline detection background task
    task = asyncio.create_task(check_offline_collectors())
    yield
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    notification_service.set_ws_manager(None, None)


app = FastAPI(
    title="SentinelOps AI",
    description="Secure AIOps Observability Platform — CICADA 2026 Hackathon",
    version="1.0.0",
    lifespan=lifespan,
    openapi_url=None if production else "/openapi.json",
)

# CORS — allow the React frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register all API routers ──────────────────────────────────────────────────
from .routers import auth, collectors, telemetry, alerts, incidents, notifications, aiops, privacy, reports, remediation, performance

app.include_router(auth.router)
app.include_router(collectors.router)
app.include_router(telemetry.router)
app.include_router(alerts.router)
app.include_router(incidents.router)
app.include_router(notifications.router)
app.include_router(aiops.router)
app.include_router(privacy.router)
app.include_router(reports.router)
app.include_router(reports.status_router)
app.include_router(remediation.router)
app.include_router(performance.router)


@app.get("/health")
def health_check():
    """Simple health check endpoint — used by monitoring and load balancers."""
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok", "service": "SentinelOps AI", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.websocket("/api/v1/notifications/ws")
async def websocket_notifications(websocket: WebSocket):
    if websocket.headers.get("origin") not in origins:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    tenant_id = None
    try:
        # The first encrypted frame carries the JWT. URLs and access logs omit it.
        token = await asyncio.wait_for(websocket.receive_text(), timeout=5)
        claims = decode_token(token)
        with SessionLocal() as db:
            user = get_current_user(token, db)
            tenant_id = user.tenant_id
        expiry = float(claims["exp"])
        manager.connect(websocket, tenant_id)
        await websocket.send_json({"type": "connected", "tenant_id": tenant_id})
        while True:
            await asyncio.wait_for(websocket.receive_text(), timeout=expiry - time.time())
    except WebSocketDisconnect:
        pass
    except (JWTError, HTTPException, TimeoutError, KeyError, ValueError):
        await websocket.close(code=1008)
    finally:
        if tenant_id is not None:
            manager.disconnect(websocket, tenant_id)
