"""
telemetry-simulator/scenarios/latency_rise.py
"""
import random

_step = 0

def generate(tick: int = 0) -> list:
    global _step
    _step += 1
    latency = min(15.0 + (_step * 20.0), 600.0) + random.uniform(-10, 10)
    return [
        ("src-alpha-01", "cpu", round(28.0 + random.uniform(-3, 3), 2)),
        ("src-alpha-01", "memory", round(52.0 + random.uniform(-3, 3), 2)),
        ("src-alpha-01", "disk", round(61.0, 2)),
        ("src-alpha-01", "network", round(latency, 2)),
    ]

def reset():
    global _step
    _step = 0
