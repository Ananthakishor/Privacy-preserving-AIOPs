"""
backend/app/aiops/baseline.py
Maintains per-source, per-category rolling baselines for anomaly detection.

A baseline is computed from the last N metric values for a given
(source_id, category) pair. When fewer than MIN_SAMPLES values exist,
the system is in "warm-up" state and anomaly detection is suspended.
"""
import numpy as np
from collections import defaultdict, deque
from typing import Optional, Tuple

# Minimum samples needed before we can establish a reliable baseline
MIN_SAMPLES = 10
# How many recent samples to keep in the rolling window
WINDOW_SIZE = 50

# In-memory baseline store: {(source_id, category): deque of float values}
# In production this would be persisted; for the prototype in-memory is fine
_baselines: dict = defaultdict(lambda: deque(maxlen=WINDOW_SIZE))


def add_sample(source_id: str, category: str, value: float):
    """Add a new metric sample to the rolling baseline window."""
    key = (source_id, category)
    _baselines[key].append(value)


def get_baseline_stats(source_id: str, category: str) -> Optional[Tuple[float, float, int]]:
    """
    Return (mean, std_dev, sample_count) for the current baseline window.
    Returns None if fewer than MIN_SAMPLES are available (warm-up state).
    """
    key = (source_id, category)
    samples = list(_baselines[key])

    if len(samples) < MIN_SAMPLES:
        return None  # Not enough history — warm-up state

    arr = np.array(samples, dtype=float)
    mean = float(np.mean(arr))
    std = float(np.std(arr))

    # Avoid division by zero for perfectly stable metrics
    if std < 0.01:
        std = 0.01

    return mean, std, len(samples)


def is_warmup(source_id: str, category: str) -> bool:
    """Return True if not enough samples exist to establish a baseline."""
    return len(_baselines[(source_id, category)]) < MIN_SAMPLES


def reset_baseline(source_id: str, category: str):
    """Clear the baseline for a source/category pair (useful for tests)."""
    key = (source_id, category)
    if key in _baselines:
        _baselines[key].clear()
