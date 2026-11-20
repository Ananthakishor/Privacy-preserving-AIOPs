"""
telemetry-simulator/scenarios/out_of_order.py
Sends events with timestamps 2 minutes in the past to test out-of-order handling.
"""
import random
from datetime import datetime, timezone, timedelta

def generate(tick: int = 0) -> list:
    # Event time is 2 minutes ago — arrives late
    past_time = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    return [
        ("src-alpha-01", "cpu", round(28.0 + random.uniform(-5, 5), 2), None, past_time),
    ]
