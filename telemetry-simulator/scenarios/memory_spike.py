"""
telemetry-simulator/scenarios/memory_spike.py
"""
import random

_step = 0

def generate(tick: int = 0) -> list:
    global _step
    _step += 1
    mem = min(45.0 + (_step * 3.5), 94.0) + random.uniform(-2, 2)
    return [
        ("src-alpha-01", "cpu", round(28.0 + random.uniform(-3, 3), 2)),
        ("src-alpha-01", "memory", round(mem, 2)),
        ("src-alpha-01", "disk", round(61.0, 2)),
        ("src-alpha-01", "network", round(20.0, 2)),
    ]

def reset():
    global _step
    _step = 0
