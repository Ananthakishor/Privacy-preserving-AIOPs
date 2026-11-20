"""
backend/app/aiops/baseline.py
Maintains per-source, per-category rolling baselines for anomaly detection.

Uses SQLite for persistence so the Z-score engine survives backend restarts.
Without persistence, the baseline would be lost on every restart and the
engine would spend the first 10 data points in "warm-up" state each time.

A baseline is computed from the last WINDOW_SIZE metric values for a given
(source_id, tenant_id, category) triple. When fewer than MIN_SAMPLES values
exist, the system is in "warm-up" state and anomaly detection is suspended.

Design: one row per (source_id, category) in the aiops_baselines table.
The row is upserted on every new sample.
"""
import json
import numpy as np
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from ..models.aiops_baseline import AIOpsBaseline

# Minimum samples needed before we can establish a reliable baseline
MIN_SAMPLES = 10
# How many recent samples to keep in the rolling window
WINDOW_SIZE = 50


def add_sample(
    db: Session,
    source_id: str,
    category: str,
    tenant_id: str,
    value: float,
):
    """
    Add a new metric sample to the rolling baseline window in SQLite.
    Creates the row if it doesn't exist (upsert pattern).
    """
    row = db.query(AIOpsBaseline).filter(
        AIOpsBaseline.source_id == source_id,
        AIOpsBaseline.category == category,
        AIOpsBaseline.tenant_id == tenant_id,
    ).first()

    if row is None:
        # First sample for this source/category — create a new baseline row
        row = AIOpsBaseline(
            source_id=source_id,
            category=category,
            tenant_id=tenant_id,
            samples_json="[]",
            mean=0.0,
            std_dev=0.0,
            sample_count=0,
        )
        db.add(row)
        db.flush()  # Assign ID without committing

    # Deserialize existing samples, append new value, cap at WINDOW_SIZE
    samples = json.loads(row.samples_json or "[]")
    samples.append(float(value))
    if len(samples) > WINDOW_SIZE:
        samples = samples[-WINDOW_SIZE:]

    # Recompute statistics
    arr = np.array(samples, dtype=float)
    row.samples_json = json.dumps(samples)
    row.sample_count = len(samples)
    row.mean = float(np.mean(arr))
    row.std_dev = float(np.std(arr))

    db.commit()


def get_baseline_stats(
    db: Session,
    source_id: str,
    category: str,
    tenant_id: str,
) -> Optional[Tuple[float, float, int]]:
    """
    Return (mean, std_dev, sample_count) for the current baseline window.
    Returns None if fewer than MIN_SAMPLES are available (warm-up state).
    """
    row = db.query(AIOpsBaseline).filter(
        AIOpsBaseline.source_id == source_id,
        AIOpsBaseline.category == category,
        AIOpsBaseline.tenant_id == tenant_id,
    ).first()

    if row is None or row.sample_count < MIN_SAMPLES:
        return None  # Not enough history — warm-up state

    std = row.std_dev
    # Avoid division by zero for perfectly stable metrics
    if std < 0.01:
        std = 0.01

    return row.mean, std, row.sample_count


def is_warmup(
    db: Session,
    source_id: str,
    category: str,
    tenant_id: str,
) -> bool:
    """Return True if not enough samples exist to establish a baseline."""
    row = db.query(AIOpsBaseline).filter(
        AIOpsBaseline.source_id == source_id,
        AIOpsBaseline.category == category,
        AIOpsBaseline.tenant_id == tenant_id,
    ).first()
    return row is None or row.sample_count < MIN_SAMPLES


def reset_baseline(
    db: Session,
    source_id: str,
    category: str,
    tenant_id: str,
):
    """Clear the baseline for a source/category pair (useful for tests)."""
    row = db.query(AIOpsBaseline).filter(
        AIOpsBaseline.source_id == source_id,
        AIOpsBaseline.category == category,
        AIOpsBaseline.tenant_id == tenant_id,
    ).first()
    if row:
        row.samples_json = "[]"
        row.sample_count = 0
        row.mean = 0.0
        row.std_dev = 0.0
        db.commit()
