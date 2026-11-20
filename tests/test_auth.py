"""
tests/test_auth.py
Test 3: User authentication tests.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest


def test_login_success(client):
    """Valid credentials return a JWT token."""
    r = client.post("/api/v1/auth/login", data={
        "username": "admin@alpha.local", "password": "SentinelAdmin2026!"
    })
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["role"] == "admin"
    assert data["tenant_id"] == "tenant-alpha"


def test_login_wrong_password(client):
    """Wrong password must return 401."""
    r = client.post("/api/v1/auth/login", data={
        "username": "admin@alpha.local", "password": "wrongpassword"
    })
    assert r.status_code == 401


def test_login_nonexistent_user(client):
    """Non-existent email must return 401."""
    r = client.post("/api/v1/auth/login", data={
        "username": "nobody@nowhere.com", "password": "test"
    })
    assert r.status_code == 401


def test_protected_route_requires_token(client):
    """Protected endpoints must return 401 without a token."""
    r = client.get("/api/v1/telemetry/metrics")
    assert r.status_code == 401


def test_me_returns_correct_user(client, auth_headers):
    """GET /me must return the authenticated user's info."""
    r = client.get("/api/v1/auth/me", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "admin@alpha.local"
    assert data["role"] == "admin"
