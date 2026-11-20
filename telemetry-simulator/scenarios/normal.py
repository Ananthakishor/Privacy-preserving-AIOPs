"""
telemetry-simulator/scenarios/normal.py
Steady-state normal telemetry for two simulated servers.
"""
import random
import math


def generate(tick: int = 0) -> list:
    """
    Generate normal operating metrics for two servers.
    tick is used to add slight variation over time (sine wave).
    Returns list of (source_id, category, value) tuples.
    """
    # Slight sine wave to make charts look realistic
    variation = math.sin(tick * 0.1) * 5

    return [
        # Server Alpha-01: moderate CPU, normal memory
        ("src-alpha-01", "cpu", round(28.0 + variation + random.uniform(-3, 3), 2)),
        ("src-alpha-01", "memory", round(52.0 + variation * 0.5 + random.uniform(-2, 2), 2)),
        ("src-alpha-01", "disk", round(61.0 + random.uniform(-0.5, 0.5), 2)),
        ("src-alpha-01", "network", round(18.0 + random.uniform(-5, 5), 2)),  # latency ms

        # Server Alpha-02: lower CPU, higher memory
        ("src-alpha-02", "cpu", round(15.0 + variation * 0.5 + random.uniform(-2, 2), 2)),
        ("src-alpha-02", "memory", round(68.0 + random.uniform(-3, 3), 2)),
        ("src-alpha-02", "disk", round(45.0 + random.uniform(-0.5, 0.5), 2)),
        ("src-alpha-02", "network", round(12.0 + random.uniform(-3, 3), 2)),
    ]
