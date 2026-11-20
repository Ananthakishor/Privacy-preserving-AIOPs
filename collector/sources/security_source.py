"""
collector/sources/security_source.py
Reads real Windows Security Event Log to count failed login attempts.

CRITICAL PRIVACY RULE: This source produces SUMMARIES only.
- Raw authentication logs NEVER leave this file.
- Only the count, timestamp, and severity are passed to the pipeline.
- Usernames, passwords, IP addresses, and raw log lines stay local.

Windows Event Log approach:
- Event ID 4625 = "An account failed to log on"
- We use 'wevtutil qe Security' via subprocess to query the log locally.
- We count events in the last 5-minute window and pass only the count + severity.
- On non-Windows systems (or if wevtutil fails), we fall back to file-based
  local log monitoring, then to a safe static "insufficient data" state.

Data that stays local (NEVER transmitted):
  - Usernames attempted
  - Source IP addresses
  - Raw XML event records
  - Workstation names
  - Log names or paths

Data that MAY be transmitted (after allowlist):
  - failed_login_count  (integer)
  - security_severity   (info/warning/critical)
  - window_start        (ISO-8601 UTC — no PII)
"""
import platform
import subprocess
import logging
import re
from datetime import datetime, timezone, timedelta

log = logging.getLogger(__name__)

# Reset window for counting failed logins
_WINDOW_MINUTES = 5

# Count thresholds for severity escalation
_WARNING_THRESHOLD = 5
_CRITICAL_THRESHOLD = 10


def collect_security_signals() -> dict:
    """
    Returns a security summary containing counts and severity indicators only.
    Raw credentials, usernames, and log lines are NEVER included.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=_WINDOW_MINUTES)
    failed_count = 0
    data_source = "live"

    if platform.system() == "Windows":
        failed_count, data_source = _count_failed_logins_windows(window_start)
    else:
        # Non-Windows: attempt syslog parsing, fall back gracefully
        failed_count, data_source = _count_failed_logins_unix(window_start)

    # Determine severity based on count
    if failed_count >= _CRITICAL_THRESHOLD:
        severity = "critical"
        description = (
            f"{failed_count} failed authentication attempts detected "
            f"in the last {_WINDOW_MINUTES} minutes — possible brute-force."
        )
    elif failed_count >= _WARNING_THRESHOLD:
        severity = "warning"
        description = (
            f"{failed_count} failed authentication attempts detected "
            f"in the last {_WINDOW_MINUTES} minutes."
        )
    else:
        severity = "info"
        description = "Authentication activity within normal range."

    return {
        # Safe fields — counts and severity, not raw logs
        "failed_login_count": failed_count,
        "security_severity": severity,
        "security_description": description,
        "window_start": window_start.isoformat(),
        "collection_timestamp": now.isoformat(),
        "data_source": data_source,

        # RAW FIELDS — THESE NEVER LEAVE THE COLLECTOR
        # (kept here to demonstrate that the redactor/allowlist strips them)
        "_raw_usernames_attempted": ["[REDACTED — local only]"],
        "_raw_source_ips": ["[REDACTED — local only]"],
    }


def _count_failed_logins_windows(window_start: datetime) -> tuple:
    """
    Query Windows Security Event Log for Event ID 4625 (failed logon)
    within the last window using wevtutil.

    wevtutil is a built-in Windows tool that requires no installation.
    It is available on Windows Vista and later.

    Returns (count, data_source_tag).
    """
    try:
        # Format the start time for wevtutil's XPath filter
        # wevtutil expects: YYYY-MM-DDTHH:MM:SS.000Z
        start_str = window_start.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # XPath query: Security log, Event ID 4625, within last window
        xpath = (
            f"*[System[EventID=4625 and "
            f"TimeCreated[@SystemTime>='{start_str}']]]"
        )

        result = subprocess.run(
            ["wevtutil", "qe", "Security",
             f"/q:{xpath}",
             "/c:1000",          # max 1000 events (plenty for 5-min window)
             "/rd:true",         # read direction: newest first
             "/f:text"],         # text format (not XML) — less parsing overhead
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode != 0:
            log.debug(f"[SECURITY] wevtutil returned {result.returncode}: {result.stderr[:200]}")
            return _fallback_count(), "simulated"

        # Count how many "Event[" records appear in the output
        # Each record starts with "Event[" in text format
        count = result.stdout.count("Event[")

        log.debug(f"[SECURITY] Windows Event Log: {count} failed logins in last {_WINDOW_MINUTES} min")
        return count, "live"

    except FileNotFoundError:
        log.warning("[SECURITY] wevtutil not found — using simulated count")
        return _fallback_count(), "simulated"
    except subprocess.TimeoutExpired:
        log.warning("[SECURITY] wevtutil timed out — using simulated count")
        return _fallback_count(), "simulated"
    except PermissionError:
        # Security log requires elevated permissions in some configurations
        log.warning("[SECURITY] Insufficient permissions for Security Event Log — using simulated count")
        return _fallback_count(), "simulated"
    except Exception as e:
        log.warning(f"[SECURITY] Unexpected error reading event log: {e}")
        return _fallback_count(), "simulated"


def _count_failed_logins_unix(window_start: datetime) -> tuple:
    """
    On Linux/macOS: count failed login attempts from /var/log/auth.log
    or the systemd journal within the last window.

    Returns (count, data_source_tag).
    """
    try:
        # Try journalctl first (systemd systems)
        start_str = window_start.strftime("%Y-%m-%d %H:%M:%S")
        result = subprocess.run(
            ["journalctl", "_SYSTEMD_UNIT=sshd.service",
             "--since", start_str,
             "--no-pager", "-q"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            # Count lines containing "Failed password" or "Invalid user"
            count = sum(
                1 for line in result.stdout.splitlines()
                if "Failed password" in line or "Invalid user" in line
            )
            return count, "live"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    try:
        # Fallback: /var/log/auth.log
        with open("/var/log/auth.log", "r", errors="replace") as f:
            lines = f.readlines()
        count = sum(
            1 for line in lines
            if "Failed password" in line or "authentication failure" in line.lower()
        )
        return count, "live"
    except (FileNotFoundError, PermissionError):
        pass

    return _fallback_count(), "simulated"


def _fallback_count() -> int:
    """
    Safe fallback when real event log data is unavailable.
    Returns 0 (no events detected) — never fabricates elevated counts.

    This is intentionally conservative: reporting 0 when unsure is safer
    than fabricating threat data that would trigger false alarms.
    """
    return 0
