"""
backend/app/services/health_service.py
Classifies system health into one of four states: Excellent, Good, Fair, Poor.

The classification uses configurable thresholds and clear reasoning.
Stale data (no heartbeat within 60s) always downgrades to Poor —
the system never shows "last known good" as if it were current.
"""
from datetime import datetime, timezone
from typing import Tuple


# Default thresholds — these can be made configurable via Settings
THRESHOLDS = {
    "excellent": {"cpu_max": 60, "mem_max": 70, "latency_max": 100, "packet_loss_max": 0},
    "good":      {"cpu_max": 75, "mem_max": 80, "latency_max": 200, "packet_loss_max": 1},
    "fair":      {"cpu_max": 90, "mem_max": 90, "latency_max": 500, "packet_loss_max": 5},
    # Poor: anything exceeding Fair thresholds, or stale data
}


def classify_health(
    cpu: float = 0,
    memory: float = 0,
    latency_ms: float = 0,
    packet_loss: float = 0,
    has_critical_alert: bool = False,
    is_stale: bool = False,
    collector_offline: bool = False,
) -> Tuple[str, str]:
    """
    Classify health state and return (state, reason) tuple.

    Args:
        cpu: CPU usage percentage (0-100)
        memory: Memory usage percentage (0-100)
        latency_ms: Network latency in milliseconds
        packet_loss: Packet loss percentage (0-100)
        has_critical_alert: Whether there is an active critical security alert
        is_stale: Whether the last telemetry is older than the offline threshold
        collector_offline: Whether the collector itself is offline

    Returns:
        Tuple of (health_state_string, reason_string)
    """
    # Stale or offline data ALWAYS → Poor
    # This prevents showing old "healthy" metrics as current
    if is_stale:
        return "poor", "Telemetry data is stale — no recent updates received"
    if collector_offline:
        return "poor", "Collector is offline — no data being received"
    if has_critical_alert:
        return "poor", "Active critical security or availability alert"

    # Check Poor thresholds first (most severe)
    if cpu >= 90:
        return "poor", f"CPU usage critical at {cpu:.1f}% (threshold: 90%)"
    if memory >= 90:
        return "poor", f"Memory usage critical at {memory:.1f}% (threshold: 90%)"
    if latency_ms > 500:
        return "poor", f"Network latency severely elevated at {latency_ms:.0f}ms (threshold: 500ms)"
    if packet_loss > 5:
        return "poor", f"High packet loss at {packet_loss:.1f}% (threshold: 5%)"

    # Check Fair thresholds
    if cpu >= 75:
        return "fair", f"CPU usage elevated at {cpu:.1f}% (threshold: 75%)"
    if memory >= 80:
        return "fair", f"Memory usage elevated at {memory:.1f}% (threshold: 80%)"
    if latency_ms > 200:
        return "fair", f"Network latency elevated at {latency_ms:.0f}ms (threshold: 200ms)"
    if packet_loss > 1:
        return "fair", f"Packet loss detected at {packet_loss:.1f}% (threshold: 1%)"

    # Check Good thresholds
    if cpu >= 60:
        return "good", f"CPU usage slightly elevated at {cpu:.1f}% (threshold: 60%)"
    if memory >= 70:
        return "good", f"Memory usage slightly elevated at {memory:.1f}% (threshold: 70%)"
    if latency_ms > 100:
        return "good", f"Minor latency at {latency_ms:.0f}ms (threshold: 100ms)"

    # Everything within normal range
    return "excellent", "All metrics within expected baselines"
