"""
tests/conftest.py
Shared pytest fixtures for all test modules.
"""
import sys
import os
import pytest
import tempfile
from pathlib import Path

# The suite seeds demo data. Keep those writes outside every application database.
_test_files = tempfile.TemporaryDirectory(prefix="sentinelops-tests-", ignore_cleanup_errors=True)
_test_dir = Path(_test_files.name)
os.environ["DATABASE_URL"] = "sqlite:///" + str(_test_dir / "app.db")
os.environ["AUDIT_LOG_FILE"] = str(_test_dir / "audit.jsonl")
os.environ["APP_ENV"] = "development"

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal, init_db, engine, Base
from backend.app.models import *


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables and seed test data."""
    init_db()
    # Seed data for all tests (idempotent — skips if already seeded)
    try:
        from backend.seed_data import seed
        seed()
    except Exception:
        pass
    yield
    # Cleanup handled by test isolation


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def db():
    """Database session for direct model manipulation in tests."""
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def admin_token(client):
    """Get JWT token for admin user (requires seeded data)."""
    from backend.seed_data import seed
    seed()
    response = client.post("/api/v1/auth/login", data={
        "username": "admin@alpha.local",
        "password": "SentinelAdmin2026!"
    })
    return response.json().get("access_token", "")


@pytest.fixture
def viewer_beta_token(client):
    """Get JWT token for tenant-beta viewer."""
    response = client.post("/api/v1/auth/login", data={
        "username": "viewer@beta.local",
        "password": "SentinelView2026!"
    })
    return response.json().get("access_token", "")


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def beta_headers(viewer_beta_token):
    return {"Authorization": f"Bearer {viewer_beta_token}"}
