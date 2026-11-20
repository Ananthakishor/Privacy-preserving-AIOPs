"""
collector/buffer/queue.py
SQLite-backed local buffer queue for approved metadata payloads.

When the SaaS backend is unreachable, payloads are stored here and
retried later. Records are NEVER deleted until delivery is acknowledged
by the backend (HTTP 200/201 response with the event_id confirmed).

This provides:
- Durable storage across collector restarts
- Ordered delivery (by created_at)
- Delivery status tracking
- Idempotency (backend also enforces uniqueness on event_id)
"""
import sqlite3
import json
import os
from datetime import datetime, timezone
from ..config import config


def _get_connection():
    """Get a SQLite connection to the local buffer database."""
    db_path = config.LOCAL_DB_PATH
    # Handle sqlite:/// prefix
    db_path = db_path.replace("sqlite:///", "").replace("sqlite://./", "./")
    # Use absolute path relative to collector directory
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db_path.lstrip("./"))
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_buffer():
    """Create the buffer queue table if it doesn't exist."""
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payload_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            retry_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            delivered_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def enqueue(payload: dict):
    """Add an approved payload to the local buffer queue."""
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO payload_queue (event_id, payload_json, status, created_at) VALUES (?, ?, 'pending', ?)",
            (payload["event_id"], json.dumps(payload), datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
    finally:
        conn.close()


def get_pending(limit: int = 50) -> list:
    """Get pending payloads ordered by creation time (oldest first)."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT event_id, payload_json, retry_count FROM payload_queue WHERE status = 'pending' ORDER BY created_at ASC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        return [{"event_id": row[0], "payload": json.loads(row[1]), "retry_count": row[2]} for row in rows]
    finally:
        conn.close()


def mark_delivered(event_id: str):
    """Mark a payload as successfully delivered. Keep the record for audit."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE payload_queue SET status = 'delivered', delivered_at = ? WHERE event_id = ?",
            (datetime.now(timezone.utc).isoformat(), event_id)
        )
        conn.commit()
    finally:
        conn.close()


def increment_retry(event_id: str):
    """Increment the retry counter for a failed delivery attempt."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE payload_queue SET retry_count = retry_count + 1 WHERE event_id = ?",
            (event_id,)
        )
        conn.commit()
    finally:
        conn.close()


def count_pending() -> int:
    """Return the number of pending (undelivered) payloads."""
    conn = _get_connection()
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM payload_queue WHERE status = 'pending'")
        return cursor.fetchone()[0]
    finally:
        conn.close()


def count_delivered() -> int:
    """Return the number of successfully delivered payloads."""
    conn = _get_connection()
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM payload_queue WHERE status = 'delivered'")
        return cursor.fetchone()[0]
    finally:
        conn.close()
