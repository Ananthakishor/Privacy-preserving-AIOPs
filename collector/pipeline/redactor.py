"""
collector/pipeline/redactor.py
Scans event fields for secret patterns and replaces them with [REDACTED].

This is a defense-in-depth measure. The primary protection is the allow-list
(only approved fields are transmitted). The redactor adds a second layer by
scanning string values for known secret patterns even before allow-listing.

Patterns detected:
- password=... / passwd=...
- token=... / api_key=...
- Bearer <value>
- Authorization: ...
- secret=... / credential=...
- Any value matching common secret formats
"""
import re
from typing import Any

# Patterns that indicate a secret value
# Using word-boundary patterns to avoid false positives
SECRET_PATTERNS = [
    re.compile(r'(password|passwd|pwd)\s*[=:]\s*\S+', re.IGNORECASE),
    re.compile(r'(token|api_key|apikey|secret|credential|auth_token)\s*[=:]\s*\S+', re.IGNORECASE),
    re.compile(r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', re.IGNORECASE),
    re.compile(r'Authorization\s*:\s*\S+', re.IGNORECASE),
    re.compile(r'[A-Za-z0-9]{20,}[A-Za-z0-9+/=]{10,}'),  # Long base64-like strings (API keys)
]

# Fields that should ALWAYS be dropped (never sent even with allow-list)
ALWAYS_DROP_FIELDS = {
    "_raw_usernames", "_raw_source_ips", "_raw_usernames_attempted",
    "_raw_config_snippet", "raw_config_snippet", "hostname",
    "raw_hostname", "_raw_log_line", "password", "passwd", "token",
    "api_key", "secret", "credential", "auth", "authorization",
}


def redact_event(event: dict) -> dict:
    """
    Scan all string values in an event and redact secret patterns.
    Also removes fields that are always sensitive.

    Returns a new dict with secrets replaced by [REDACTED].
    """
    redacted = {}
    for key, value in event.items():
        # Drop always-sensitive field names
        if key.lower() in ALWAYS_DROP_FIELDS or key.startswith("_raw"):
            continue  # Drop the field entirely

        redacted[key] = _redact_value(value)

    return redacted


def _redact_value(value: Any) -> Any:
    """Recursively scan and redact a value."""
    if isinstance(value, str):
        return _redact_string(value)
    elif isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_redact_value(item) for item in value]
    return value


def _redact_string(text: str) -> str:
    """Replace secret patterns in a string with [REDACTED]."""
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            # Replace the matched portion with a safe placeholder
            text = pattern.sub("[REDACTED]", text)
    return text


def contains_secret(text: str) -> bool:
    """Check if a string contains any secret patterns (for testing)."""
    return any(p.search(text) for p in SECRET_PATTERNS)
