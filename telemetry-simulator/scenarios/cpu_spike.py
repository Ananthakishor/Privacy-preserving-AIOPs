"""
telemetry-simulator/scenarios/cpu_spike.py
CPU gradually ramps from 30% to 96% over 30 seconds then stays elevated.
"""
import random

_spike_step = 0

def generate(tick: int = 0) -> list:
    global _spike_step
    _spike_step += 1

    # Ramp from 30% to 96% over 20 steps, then stay high
    ramp = min(30.0 + (_spike_step * 3.3), 96.0)
    cpu = round(ramp + random.uniform(-2, 2), 2)

    return [
        ("src-alpha-01", "cpu", cpu),
        ("src-alpha-01", "memory", round(55.0 + random.uniform(-3, 3), 2)),
        ("src-alpha-01", "disk", round(61.0, 2)),
        ("src-alpha-01", "network", round(20.0 + random.uniform(-5, 5), 2)),
    ]

def reset():
    global _spike_step
    _spike_step = 0
