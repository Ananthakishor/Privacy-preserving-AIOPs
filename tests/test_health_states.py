"""
tests/test_health_states.py
Test 6: Health state classification.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.app.services.health_service import classify_health


def test_excellent_state():
    state, reason = classify_health(cpu=30, memory=50, latency_ms=50)
    assert state == "excellent"


def test_good_state_elevated_cpu():
    state, reason = classify_health(cpu=65, memory=55, latency_ms=50)
    assert state == "good"
    assert "CPU" in reason


def test_fair_state_high_cpu():
    state, reason = classify_health(cpu=80, memory=55, latency_ms=50)
    assert state == "fair"


def test_poor_state_critical_cpu():
    state, reason = classify_health(cpu=92, memory=55, latency_ms=50)
    assert state == "poor"
    assert "CPU" in reason


def test_poor_state_stale_data():
    """Stale data must always result in Poor regardless of metric values."""
    state, reason = classify_health(cpu=5, memory=5, is_stale=True)
    assert state == "poor"
    assert "stale" in reason.lower()


def test_poor_state_collector_offline():
    state, reason = classify_health(collector_offline=True)
    assert state == "poor"
    assert "offline" in reason.lower()


def test_poor_state_critical_security():
    state, reason = classify_health(has_critical_alert=True)
    assert state == "poor"


def test_fair_state_latency():
    state, reason = classify_health(cpu=20, memory=30, latency_ms=300)
    assert state == "fair"
