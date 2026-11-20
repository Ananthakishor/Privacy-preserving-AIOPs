"""
collector/sources/security_source.py
Generates security signal summaries locally.

CRITICAL PRIVACY RULE: This source produces SUMMARIES only.
- Raw authentication logs NEVER leave this file.
- Only the count, timestamp, and severity are passed to the pipeline.
- Usernames, passwords, IP addresses, and raw log lines stay local.
"""
import random
from datetime import datetime, timezone


# Simulated local authentication event buffer
# In production, this would read from /var/log/auth.log or Windows Event Log
_failed_login_count = 0
_last_reset_time = datetime.now(timezone.utc)


def collect_security_signals() -> dict:
    """
    Returns a security summary containing counts and severity indicators only.
    Raw credentials, usernames, and log lines are NEVER included.
    """
    global _failed_login_count, _last_reset_time

    # Simulate occasional failed logins
    if random.random() < 0.1:
        _failed_login_count += random.randint(1, 3)

    # Reset counter every 5 minutes
    now = datetime.now(timezone.utc)
    elapsed = (now - _last_reset_time).total_seconds()
    if elapsed > 300:
        _failed_login_count = 0
        _last_reset_time = now

    # Determine security severity based on failed login count
    if _failed_login_count >= 10:
        severity = "critical"
        description = f"{_failed_login_count} failed authentication attempts in the last 5 minutes"
    elif _failed_login_count >= 5:
        severity = "warning"
        description = f"{_failed_login_count} failed authentication attempts detected"
    else:
        severity = "info"
        description = "Authentication activity within normal range"

    return {
        # Safe fields — counts and severity, not raw logs
        "failed_login_count": _failed_login_count,
        "security_severity": severity,
        "security_description": description,
        "window_start": _last_reset_time.isoformat(),
        "collection_timestamp": now.isoformat(),

        # RAW FIELDS — THESE NEVER LEAVE THE COLLECTOR
        # (kept here to demonstrate that the redactor/allowlist strips them)
        "_raw_usernames_attempted": ["root", "admin", "user1"],  # SENSITIVE — will be dropped
        "_raw_source_ips": ["192.168.1.100", "10.0.0.5"],         # SENSITIVE — will be dropped
    }
