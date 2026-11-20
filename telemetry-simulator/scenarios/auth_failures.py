"""
telemetry-simulator/scenarios/auth_failures.py
Simulates a brute-force attack: repeated failed logins (count only, no raw credentials).
"""
import random

_step = 0

def generate(tick: int = 0) -> list:
    global _step
    _step += 1
    # Escalating failed login count
    failed_count = min(1 + _step * 2, 25)
    return [
        ("src-alpha-01", "cpu", round(28.0 + random.uniform(-3, 3), 2)),
        ("src-alpha-01", "memory", round(52.0 + random.uniform(-2, 2), 2)),
        ("src-alpha-01", "security", float(failed_count)),  # Count only — not raw credentials
    ]

def reset():
    global _step
    _step = 0
