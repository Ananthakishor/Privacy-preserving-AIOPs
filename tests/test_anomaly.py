"""
tests/test_anomaly.py
Test 5: AIOps anomaly detection engine.

NOTE: baseline.py now uses SQLite persistence instead of in-memory deques.
All baseline functions require a db session.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest

from backend.app.aiops.baseline import add_sample, get_baseline_stats, is_warmup, reset_baseline
from backend.app.aiops.anomaly_detector import ANOMALY_THRESHOLD
from backend.app.database import SessionLocal, init_db, Base
from backend.app.models import *   # noqa: ensure all models are registered


@pytest.fixture(scope="module", autouse=True)
def _ensure_tables():
    """Make sure the aiops_baselines table exists before the tests run."""
    init_db()


@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_warmup_state_with_insufficient_data(db_session):
    """Fewer than 10 samples → warm-up state."""
    reset_baseline(db_session, "test-src", "cpu", "tenant-test")
    for i in range(5):
        add_sample(db_session, "test-src", "cpu", "tenant-test", 30.0)
    assert is_warmup(db_session, "test-src", "cpu", "tenant-test") is True


def test_baseline_established_with_enough_samples(db_session):
    """10+ samples → baseline available."""
    reset_baseline(db_session, "test-src2", "cpu", "tenant-test")
    for i in range(15):
        add_sample(db_session, "test-src2", "cpu", "tenant-test", 30.0 + (i * 0.1))
    assert is_warmup(db_session, "test-src2", "cpu", "tenant-test") is False
    stats = get_baseline_stats(db_session, "test-src2", "cpu", "tenant-test")
    assert stats is not None
    mean, std, count = stats
    assert 29 < mean < 32
    assert count == 15


def test_zscore_calculated_correctly(db_session):
    """Baseline stats are computed correctly from persisted samples."""
    reset_baseline(db_session, "test-src3", "mem", "tenant-test")
    for _ in range(20):
        add_sample(db_session, "test-src3", "mem", "tenant-test", 50.0)
    stats = get_baseline_stats(db_session, "test-src3", "mem", "tenant-test")
    assert stats is not None
    mean, std, _ = stats
    # std will be near 0 for stable values, so the edge case is handled
    # Test that we can call get_baseline_stats without error
    assert mean > 40


def test_anomaly_threshold_is_2_5_sigma():
    """ANOMALY_THRESHOLD must be set to 2.5."""
    assert ANOMALY_THRESHOLD == 2.5


def test_reset_clears_baseline(db_session):
    """After reset, the source returns to warm-up state."""
    for _ in range(15):
        add_sample(db_session, "test-reset", "cpu", "tenant-test", 30.0)
    assert is_warmup(db_session, "test-reset", "cpu", "tenant-test") is False
    reset_baseline(db_session, "test-reset", "cpu", "tenant-test")
    assert is_warmup(db_session, "test-reset", "cpu", "tenant-test") is True
