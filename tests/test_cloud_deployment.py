"""Regression checks for cloud origin, socket identity, and production enrollment."""
import pytest
from starlette.websockets import WebSocketDisconnect

from backend.app.config import Settings
from backend.app.routers import collectors
from backend.app.main import app
from fastapi.testclient import TestClient


def test_production_settings():
    from secrets import token_hex
    settings = dict(app_env="production", secret_key=token_hex(32),
                    frontend_origin="https://tesseract.cv", database_url="postgresql://localhost/test")
    assert Settings(**settings).app_env == "production"
    assert Settings(**{**settings, "frontend_origin": "https://sentinelops-frontend-tau.vercel.app"}).app_env == "production"
    for invalid in ({"database_url": "sqlite:///test.db"}, {"secret_key": "demo"}, {"frontend_origin": "*"}):
        with pytest.raises(ValueError):
            Settings(**{**settings, **invalid})


def test_socket_uses_authenticated_tenant(admin_token):
    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/notifications/ws?tenant_id=other",
                                      headers={"Origin": "http://localhost:5173"}) as socket:
            socket.send_text(admin_token)
            assert socket.receive_json() == {"type": "connected", "tenant_id": "tenant-alpha"}


def test_socket_requires_token(client):
    with client.websocket_connect("/api/v1/notifications/ws",
                                  headers={"Origin": "http://localhost:5173"}) as socket:
        socket.send_text("invalid")
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == 1008


def test_enrollment_requires_provisioned_identity(client, monkeypatch):
    monkeypatch.setattr(collectors.settings, "app_env", "production")
    response = client.post("/api/v1/collectors/register", json={"name": "new"},
                           headers={"tenant-id": "tenant-alpha", "X-Collector-API-Key": "unassigned"})
    assert response.status_code == 401
