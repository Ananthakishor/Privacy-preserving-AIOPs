"""
backend/app/aiops/predictor.py
Linear trend extrapolation for predictive warnings.

This module estimates whether a metric is trending toward a critical threshold
within the next N minutes, based on recent data points.

IMPORTANT: Predictions are ESTIMATES only. They are clearly labeled as
"predictive" on the dashboard and must NOT be confused with active alerts.
The accuracy of a linear prediction depends heavily on how linear the actual
trend is — users are always shown the confidence basis.

Algorithm:
  1. Take the last K samples (default: last 20 data points) for a source/category.
  2. Fit a linear regression (NumPy polyfit degree 1).
  3. Project the fitted line forward N minutes.
  4. If the projected value exceeds the critical threshold, raise a predictive warning.

We use linear regression because it is:
  - Explainable: slope and intercept are human-readable
  - Deterministic: same inputs always produce the same output
  - Fast: no external model needed
  - Honest about its limitations: it's labeled as a linear estimate

This does NOT predict sudden spikes or non-linear behavior.
"""
import numpy as np
from typing import Optional
from sqlalchemy.orm import Session
from ..models.telemetry import Metric
from datetime import datetime, timezone, timedelta

# How many recent samples to use for the trend line
TREND_WINDOW_SIZE = 20
# How many minutes ahead to project
FORECAST_MINUTES = 10

# Default critical thresholds per category
# (configurable in settings in a production system)
_DEFAULT_THRESHOLDS = {
    "cpu":      {"warning": 75.0, "critical": 90.0},
    "memory":   {"warning": 80.0, "critical": 90.0},
    "disk":     {"warning": 85.0, "critical": 95.0},
    "network":  {"warning": 100.0, "critical": 200.0},   # ms
    "security": {"warning": 5.0,  "critical": 10.0},      # failed logins
}


def predict_threshold_breach(
    db: Session,
    tenant_id: str,
    source_id: str,
    category: str,
    forecast_minutes: int = FORECAST_MINUTES,
) -> Optional[dict]:
    """
    Predict whether this metric will breach its critical threshold
    within the next `forecast_minutes` minutes.

    Returns a prediction dict if a breach is projected, None otherwise.

    The returned dict contains:
      - source_id
      - category
      - current_value: most recent measured value
      - projected_value: extrapolated value at forecast horizon
      - threshold: the critical threshold
      - minutes_to_breach: estimated time until threshold is hit
      - slope: the trend slope (positive = rising, negative = falling)
      - sample_count: how many points were used for the fit
      - confidence_basis: human-readable explanation of the method
      - is_estimate: always True (never claim certainty)
    """
    thresholds = _DEFAULT_THRESHOLDS.get(category)
    if not thresholds:
        return None

    critical_threshold = thresholds["critical"]

    # Fetch last TREND_WINDOW_SIZE samples for this source/category
    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    cutoff_str = cutoff.isoformat()

    samples = (
        db.query(Metric)
        .filter(
            Metric.tenant_id == tenant_id,
            Metric.source_id == source_id,
            Metric.category == category,
            Metric.event_time >= cutoff_str,
        )
        .order_by(Metric.event_time.asc())
        .limit(TREND_WINDOW_SIZE)
        .all()
    )

    if len(samples) < 5:
        return None  # Not enough data for a meaningful trend

    # Build arrays: x = sample index (evenly spaced), y = metric values
    values = np.array([s.value for s in samples], dtype=float)
    x = np.arange(len(values), dtype=float)

    # Fit a degree-1 polynomial (linear regression) — y = slope * x + intercept
    coeffs = np.polyfit(x, values, deg=1)
    slope = float(coeffs[0])
    intercept = float(coeffs[1])

    current_value = float(values[-1])

    # Only warn about upward trends (for most metrics)
    # For network latency and security, any directional spike is concerning
    if slope <= 0:
        return None  # Trending downward — no breach risk

    # Estimate how many more samples until threshold is breached
    # projected_value = slope * (len(values) + steps) + intercept = threshold
    # steps = (threshold - intercept - slope * len(values)) / slope
    if abs(slope) < 0.001:
        return None  # Essentially flat — no breach risk

    steps_to_breach = (critical_threshold - intercept - slope * len(values)) / slope

    if steps_to_breach <= 0:
        # Already above threshold — this is an active condition, not a prediction
        return None

    # Estimate collection interval (seconds between samples)
    if len(samples) >= 2:
        try:
            t0 = datetime.fromisoformat(samples[0].event_time.replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(samples[-1].event_time.replace("Z", "+00:00"))
            interval_secs = (t1 - t0).total_seconds() / max(len(samples) - 1, 1)
        except Exception:
            interval_secs = 5.0  # Default: assume 5-second collection interval
    else:
        interval_secs = 5.0

    minutes_to_breach = (steps_to_breach * interval_secs) / 60.0

    if minutes_to_breach > forecast_minutes:
        return None  # Breach is too far in the future to warn about now

    # Project the value at the forecast horizon
    forecast_steps = (forecast_minutes * 60) / max(interval_secs, 1)
    projected_value = slope * (len(values) + forecast_steps) + intercept

    # R² goodness of fit (how reliable is this linear prediction?)
    residuals = values - (slope * x + intercept)
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((values - np.mean(values)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return {
        "source_id": source_id,
        "category": category,
        "current_value": round(current_value, 2),
        "projected_value": round(min(projected_value, 100.0), 2),
        "threshold": critical_threshold,
        "minutes_to_breach": round(minutes_to_breach, 1),
        "slope": round(slope, 4),
        "sample_count": len(samples),
        "r_squared": round(r_squared, 3),
        "confidence_basis": (
            f"Linear regression over last {len(samples)} samples "
            f"(slope={slope:.4f}/sample, R²={r_squared:.2f}). "
            f"This is a linear estimate — sudden spikes are not predicted."
        ),
        "is_estimate": True,  # Always true — never claim certainty
        "severity": "warning",
    }
