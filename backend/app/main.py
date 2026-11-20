"""
backend/app/main.py
FastAPI application entry point.

Registers all routers, configures CORS, manages WebSocket connections,
runs the collector offline detection background task, and initializes
the database on startup.
"""
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .config import get_settings
from .database import init_db, SessionLocal
from .services import notification_service

settings = get_settings()


class ConnectionManager:
    """
    Manages active WebSocket connections grouped by tenant_id.
    When a notification is created, it is broadcast to all connections
    for the relevant tenant only (enforces tenant isolation in real-time).
    """
    def __init__(self):
        # {tenant_id: [WebSocket, ...]}
        self.connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, tenant_id: str):
        await websocket.accept()
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
            self.connections[tenant_id].remove(ws)


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
        try:
            db = SessionLocal()
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
            db.close()
        except Exception:
            pass
        await asyncio.sleep(10)  # Check every 10 seconds


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize DB and start background tasks. Shutdown: clean up."""
    init_db()
    # Inject WebSocket manager into notification service
    notification_service.set_ws_manager(manager)
    # Start collector offline detection background task
    task = asyncio.create_task(check_offline_collectors())
    yield
    task.cancel()


app = FastAPI(
    title="SentinelOps AI",
    description="Secure AIOps Observability Platform — CICADA 2026 Hackathon",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the React frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://localhost:3000"],
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
    return {"status": "ok", "service": "SentinelOps AI", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.websocket("/api/v1/notifications/ws")
async def websocket_notifications(websocket: WebSocket, tenant_id: str = "tenant-alpha"):
    """
    WebSocket endpoint for real-time notification push.
    Clients connect with ?tenant_id=<tenant_id>.
    New notifications are broadcast to all connected clients for that tenant.
    """
    await manager.connect(websocket, tenant_id)
    try:
        # Send a welcome message to confirm connection
        await websocket.send_text(json.dumps({"type": "connected", "tenant_id": tenant_id}))
        # Keep the connection alive — receive any client messages (e.g. ping)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_id)
