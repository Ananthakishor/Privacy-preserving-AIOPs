"""
collector/transport/sender.py
Sends approved metadata payloads to the SaaS backend.

Delivery behavior:
- Attempts delivery immediately
- On failure: stores in SQLite buffer queue
- Retries with exponential backoff (2s, 4s, 8s... capped at 300s)
- Marks as delivered only after HTTP 200/201 ACK
- HTTP 409 = already received (idempotent) — mark as delivered
- Records delivery status in egress proof log
"""
import time
import requests
from ..config import config
from ..buffer.queue import enqueue, mark_delivered, increment_retry
from ..egress_proof.logger import log_egress, update_egress_status


def send_payload(payload: dict) -> bool:
    """
    Attempt to deliver a single approved payload to the SaaS backend.

    Returns True if delivered (or already received), False if failed.
    On failure, the payload is queued in the local SQLite buffer.
    """
    headers = {
        "X-Collector-API-Key": config.COLLECTOR_API_KEY,
        "Content-Type": "application/json",
    }

    # Log the outgoing payload to the egress proof file BEFORE sending
    log_egress(payload, status="pending")

    try:
        response = requests.post(
            config.SAAS_INGEST_URL,
            json=payload,
            headers=headers,
            timeout=10,
        )

        if response.status_code in (200, 201):
            update_egress_status(payload["event_id"], "delivered")
            mark_delivered(payload["event_id"])
            return True

        elif response.status_code == 409:
            # Already received — idempotent delivery, treat as success
            update_egress_status(payload["event_id"], "duplicate_ok")
            mark_delivered(payload["event_id"])
            return True

        else:
            # Server error — queue for retry
            update_egress_status(payload["event_id"], "failed")
            enqueue(payload)
            return False

    except requests.exceptions.ConnectionError:
        # Backend unreachable — queue for retry
        update_egress_status(payload["event_id"], "queued_offline")
        enqueue(payload)
        return False

    except Exception:
        update_egress_status(payload["event_id"], "error")
        enqueue(payload)
        return False


def retry_pending():
    """
    Attempt to deliver all pending buffered payloads.
    Uses exponential backoff between retries.
    Called periodically by the main collector loop.
    """
    from ..buffer.queue import get_pending

    pending = get_pending(limit=10)  # Process 10 at a time
    if not pending:
        return

    headers = {
        "X-Collector-API-Key": config.COLLECTOR_API_KEY,
        "Content-Type": "application/json",
    }

    for item in pending:
        payload = item["payload"]
        retry_count = item["retry_count"]

        # Exponential backoff: 2^retry * base_delay, capped at 300s
        delay = min(config.RETRY_BASE_DELAY * (2 ** retry_count), 300)

        try:
            response = requests.post(
                config.SAAS_INGEST_URL,
                json=payload,
                headers=headers,
                timeout=10,
            )

            if response.status_code in (200, 201, 409):
                mark_delivered(payload["event_id"])
                update_egress_status(payload["event_id"], "delivered_retry")
            else:
                increment_retry(payload["event_id"])

        except Exception:
            increment_retry(payload["event_id"])


def send_heartbeat(collector_id: str, cpu_pct: float, mem_pct: float, buffered_count: int):
    """Send a heartbeat to the SaaS backend."""
    headers = {"X-Collector-API-Key": config.COLLECTOR_API_KEY}
    payload = {
        "collector_id": collector_id,
        "tenant_id": config.COLLECTOR_TENANT_ID,
        "cpu_pct": cpu_pct,
        "mem_pct": mem_pct,
        "buffered_count": buffered_count,
        "version": config.COLLECTOR_VERSION,
    }
    try:
        requests.post(config.SAAS_HEARTBEAT_URL, json=payload, headers=headers, timeout=5)
    except Exception:
        pass  # Heartbeat failure is non-fatal
