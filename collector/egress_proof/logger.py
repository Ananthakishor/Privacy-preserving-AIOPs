"""
collector/egress_proof/logger.py
Records every approved outgoing payload to a local JSONL file.

This file is the EGRESS PROOF LOG — it proves what exactly left the
collector environment. It is stored LOCALLY ONLY and is never uploaded
to the SaaS backend.

The SaaS Privacy Center only shows the transfer_audit records that
the backend stores after successfully receiving a payload. The egress
proof log here is the collector-side ground truth for comparison.

Format: one JSON object per line, appended in order.
"""
import json
import os
from datetime import datetime, timezone
from ..config import config


def log_egress(payload: dict, status: str = "pending", retry_count: int = 0):
    """
    Append an egress proof entry to the local log file.

    This is called BEFORE transmission — we record what we're about to send,
    not what was acknowledged received. This proves the collector's intent.

    Args:
        payload: The approved metadata dict (allow-listed fields only)
        status: 'pending' before send, 'delivered' after ACK, 'failed' on error
        retry_count: Number of retry attempts so far
    """
    # Ensure the egress proof directory exists
    os.makedirs(os.path.dirname(config.EGRESS_LOG_PATH), exist_ok=True)

    entry = {
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "event_id": payload.get("event_id", "unknown"),
        "collector_id": payload.get("collector_id", "unknown"),
        "tenant_id": payload.get("tenant_id", "unknown"),
        "destination": config.SAAS_INGEST_URL,
        "fields_included": sorted(payload.keys()),
        "field_count": len(payload),
        "status": status,
        "retry_count": retry_count,
        "payload": payload,  # Full approved payload — never contains secrets
    }

    with open(config.EGRESS_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def update_egress_status(event_id: str, status: str, retry_count: int = 0):
    """
    Update the status of an existing egress entry.
    Since JSONL is append-only, we append an update record.
    """
    os.makedirs(os.path.dirname(config.EGRESS_LOG_PATH), exist_ok=True)

    update = {
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "event_id": event_id,
        "type": "status_update",
        "status": status,
        "retry_count": retry_count,
    }

    with open(config.EGRESS_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(update) + "\n")


def read_egress_log(last_n: int = 50) -> list:
    """Read the last N entries from the egress proof log."""
    if not os.path.exists(config.EGRESS_LOG_PATH):
        return []
    entries = []
    with open(config.EGRESS_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
    return entries[-last_n:]
