"""
telemetry-simulator/scenarios/duplicates.py
Sends the same event_id twice to test idempotent delivery.
"""
import uuid

_stored_event_id = None

def generate(tick: int = 0) -> list:
    """Returns events with the same event_id on even ticks (duplicate test)."""
    global _stored_event_id
    if tick % 2 == 0 or _stored_event_id is None:
        _stored_event_id = str(uuid.uuid4())
    # Return same event_id — backend should reject the duplicate with 409
    return [
        ("src-alpha-01", "cpu", 30.0, _stored_event_id),
    ]
