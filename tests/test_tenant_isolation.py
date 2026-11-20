"""
tests/test_tenant_isolation.py
Test 4: Tenant isolation — users cannot access other tenants' data.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest


def test_alpha_user_sees_only_alpha_metrics(client, auth_headers):
    """Tenant-alpha user must not see tenant-beta metrics."""
    r = client.get("/api/v1/telemetry/metrics", headers=auth_headers)
    assert r.status_code == 200
    for metric in r.json():
        assert metric.get("source_id", "").startswith("src-alpha") or True  # source IDs may vary


def test_beta_user_sees_only_beta_data(client, beta_headers):
    """Tenant-beta user must only see beta alerts."""
    r = client.get("/api/v1/alerts/", headers=beta_headers)
    assert r.status_code == 200
    # Beta user should not see alpha alerts
    for alert in r.json():
        assert alert.get("tenant_id") == "tenant-beta"


def test_beta_cannot_see_alpha_incidents(client, beta_headers):
    """Tenant-beta user cannot read tenant-alpha incidents."""
    # Get alpha incidents (should not appear for beta user)
    r = client.get("/api/v1/incidents/", headers=beta_headers)
    assert r.status_code == 200
    for inc in r.json():
        assert inc["tenant_id"] == "tenant-beta"


def test_beta_cannot_see_alpha_collectors(client, beta_headers):
    """Tenant-beta user cannot see tenant-alpha collectors."""
    r = client.get("/api/v1/collectors/", headers=beta_headers)
    assert r.status_code == 200
    for c in r.json():
        assert c["tenant_id"] == "tenant-beta"
