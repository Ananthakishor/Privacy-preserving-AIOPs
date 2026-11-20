"""
backend/app/services/audit_service.py
Writes immutable audit log entries to a JSONL file.

Audit events document security-relevant actions for compliance.
NEVER log passwords, tokens, API keys, or any secrets here.
"""
import json
import os
from datetime import datetime, timezone
from ..config import get_settings

settings = get_settings()


def log_audit(action: str, user_id: str, tenant_id: str, details: dict = None):
    """
    Append a JSON audit log entry to the audit log file.

    Args:
        action: What happened (e.g. "login", "incident_resolved")
        user_id: Who performed the action
        tenant_id: Which tenant this belongs to
        details: Additional safe context (no secrets)
    """
    # Ensure the logs directory exists
    os.makedirs(os.path.dirname(settings.audit_log_file), exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "details": details or {}
    }

    with open(settings.audit_log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
