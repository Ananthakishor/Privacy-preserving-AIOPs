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
import logging
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
            allow_redirects=False, timeout=10,
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

        try:
            response = requests.post(
                config.SAAS_INGEST_URL,
                json=payload,
                headers=headers,
                allow_redirects=False, timeout=10,
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
        response = requests.post(config.SAAS_HEARTBEAT_URL, json=payload, headers=headers,
                                 allow_redirects=False, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def confirm_registration():
    url = config.SAAS_HEARTBEAT_URL.removesuffix("/heartbeat") + "/register"
    headers = {"X-Collector-API-Key": config.COLLECTOR_API_KEY, "tenant-id": config.COLLECTOR_TENANT_ID}
    try:
        response = requests.post(url, headers=headers, json={"name": config.COLLECTOR_ID},
                                 allow_redirects=False, timeout=10)
    except (requests.ConnectionError, requests.Timeout):
        logging.warning("Registration endpoint unreachable. Collecting under the provisioned identity.")
        return
    if response.status_code >= 500:
        logging.warning("Registration service unavailable. Collecting under the provisioned identity.")
        return
    if response.status_code != 200 or response.json().get("collector_id") != config.COLLECTOR_ID:
        raise RuntimeError("Cloud collector registration failed. Check the assigned identity and key.")
