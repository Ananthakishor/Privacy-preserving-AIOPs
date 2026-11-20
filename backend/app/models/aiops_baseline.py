"""
backend/app/models/aiops_baseline.py
Persists rolling baseline statistics for AIOps anomaly detection.

By storing baselines in SQLite instead of in-memory, the Z-score engine
survives backend restarts. Without this, the engine would re-enter the
"warm-up" state after every restart and miss anomalies for the first
10 data points.

One row per (source_id, category) pair.
Updated in place every time a new sample is processed.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, Index
from ..database import Base


class AIOpsBaseline(Base):
    """
    Stores the rolling baseline mean, std, and sample count for a
    (source_id, metric_category) pair.

    Fields:
    - samples_json: JSON-serialized list of the last N float values
      (kept for recomputing statistics after restart)
    - mean, std_dev: computed from samples_json
    - sample_count: len(samples_json)
    - last_updated: when this row was last written
    """
    __tablename__ = "aiops_baselines"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False)      # cpu|memory|disk|network|security
    tenant_id = Column(String, nullable=False, index=True)
    mean = Column(Float, nullable=False, default=0.0)
    std_dev = Column(Float, nullable=False, default=0.0)
    sample_count = Column(Integer, nullable=False, default=0)
    # JSON list of recent float values — capped at WINDOW_SIZE
    samples_json = Column(String, nullable=False, default="[]")
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_baseline_tenant_source_cat", "tenant_id", "source_id", "category", unique=True),
    )
