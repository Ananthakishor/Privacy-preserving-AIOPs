"""
backend/app/aiops/anomaly_detector.py
Z-score based anomaly detection engine.

Goes beyond static thresholds: a value at 80% CPU is anomalous for a server
that normally runs at 20-35%, even if the fixed critical threshold is 90%.

Z-score measures how many standard deviations a value is from its recent mean.
A Z-score above ANOMALY_THRESHOLD (default 2.5) triggers an anomaly alert.

Baselines are now persisted in SQLite (via baseline.py) so detection state
survives backend restarts.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from .baseline import add_sample, get_baseline_stats, is_warmup
from ..models.alert import Alert

# Trigger anomaly when value deviates more than this many standard deviations
ANOMALY_THRESHOLD = 2.5


def _zscore_to_severity(zscore: float) -> str:
    """Map Z-score magnitude to alert severity."""
    if zscore >= 4.0:
        return "critical"
    elif zscore >= 3.0:
        return "warning"
    else:
        return "info"


def check_anomaly(
    db: Session,
    tenant_id: str,
    source_id: str,
    category: str,
    value: float,
) -> Optional[Alert]:
    """
    Check if a metric value is anomalous compared to its recent baseline.

    1. Add the value to the rolling baseline window (persisted in SQLite).
    2. If in warm-up state, return None (no detection yet).
    3. Compute Z-score: (value - mean) / std_dev
    4. If Z-score > ANOMALY_THRESHOLD, create and persist an Alert.

    Returns the Alert if an anomaly was detected, None otherwise.
    """
    # Always update baseline first (before checking)
    add_sample(db, source_id, category, tenant_id, value)

    if is_warmup(db, source_id, category, tenant_id):
        return None  # Not enough history yet

    stats = get_baseline_stats(db, source_id, category, tenant_id)
    if stats is None:
        return None

    mean, std, count = stats
    zscore = abs(value - mean) / std

    if zscore < ANOMALY_THRESHOLD:
        return None  # Normal variation

    severity = _zscore_to_severity(zscore)

    # Build a human-readable explanation from actual observed data
    direction = "above" if value > mean else "below"
    explanation = (
        f"{category.upper()} value of {value:.1f} is {direction} the recent "
        f"baseline of {mean:.1f} (±{std:.1f}) by {zscore:.1f} standard deviations. "
        f"Based on the last {count} samples."
    )

    alert = Alert(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        source_id=source_id,
        alert_type="anomaly",
        severity=severity,
        message=explanation,
        metric_category=category,
        baseline_value=round(mean, 2),
        observed_value=round(value, 2),
        deviation=round(zscore, 2),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
