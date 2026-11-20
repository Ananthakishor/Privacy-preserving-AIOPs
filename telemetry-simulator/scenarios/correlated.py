"""
telemetry-simulator/scenarios/correlated.py
CPU + Memory + Latency spike on the same server simultaneously.
This triggers incident correlation in the AIOps engine.
"""
import random

_step = 0

def generate(tick: int = 0) -> list:
    global _step
    _step += 1

    cpu = min(35.0 + (_step * 3.0), 95.0) + random.uniform(-2, 2)
    mem = min(50.0 + (_step * 2.5), 91.0) + random.uniform(-2, 2)
    latency = min(20.0 + (_step * 15.0), 450.0) + random.uniform(-10, 10)

    return [
        ("src-alpha-01", "cpu", round(cpu, 2)),
        ("src-alpha-01", "memory", round(mem, 2)),
        ("src-alpha-01", "network", round(latency, 2)),
        ("src-alpha-01", "disk", round(62.0 + random.uniform(-1, 1), 2)),
    ]

def reset():
    global _step
    _step = 0
