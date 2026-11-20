"""
backend/app/services/watsonx_service.py
IBM watsonx AI assistant integration for the "Ask Sentinel AI" feature.

CRITICAL PRIVACY RULES (enforced by this module):
  1. This service NEVER receives raw logs, passwords, tokens, or secrets.
  2. Only allow-listed metadata fields are included in the context sent to watsonx.
  3. The context is built from already-stored SaaS-tier records (no collector raw data).
  4. If watsonx is unavailable, a local rule-based answer is returned as fallback.
  5. Tenant isolation: context is always scoped to the authenticated user's tenant.

Authentication to watsonx:
  - Exchange IBM Cloud API key for a short-lived IAM access token.
  - Use the access token as Bearer in the watsonx chat endpoint.
  - The API key is never sent to the watsonx endpoint directly.
  - The IAM token expires in ~1 hour; we refresh it on demand.

Model used: ibm/granite-3-8b-instruct (available in watsonx.ai free tier)
"""
import os
import time
import logging
import requests
from typing import Optional
from sqlalchemy.orm import Session
from ..config import get_settings

log = logging.getLogger(__name__)

settings = get_settings()

# IBM IAM token endpoint — standard for all IBM Cloud services
_IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"

# Cache the IAM token to avoid requesting a new one on every query
_cached_iam_token: Optional[str] = None
_token_expires_at: float = 0.0

# Watsonx model to use — granite-4-h-small supports the text_chat function
_WATSONX_MODEL = "ibm/granite-4-h-small"

# Max tokens for the response
_MAX_NEW_TOKENS = 500


def _get_iam_token() -> Optional[str]:
    """
    Exchange the IBM Cloud API key for a short-lived IAM access token.
    Caches the token until it expires (minus 60 seconds buffer).
    Returns None if the exchange fails (network error, invalid key, etc.).
    """
    global _cached_iam_token, _token_expires_at

    # Return cached token if still valid
    if _cached_iam_token and time.time() < _token_expires_at:
        return _cached_iam_token

    api_key = settings.ibm_watsonx_api_key
    if not api_key:
        log.warning("[WATSONX] IBM_WATSONX_API_KEY not configured — AI assistant disabled")
        return None

    try:
        resp = requests.post(
            _IAM_TOKEN_URL,
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": api_key,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        _cached_iam_token = data["access_token"]
        # expires_in is typically 3600 seconds; we subtract 60s buffer
        _token_expires_at = time.time() + data.get("expires_in", 3600) - 60
        log.info("[WATSONX] IAM token refreshed successfully")
        return _cached_iam_token

    except requests.exceptions.RequestException as e:
        log.error(f"[WATSONX] IAM token exchange failed: {e}")
        return None


def _build_context(db: Session, tenant_id: str, question: str) -> str:
    """
    Build a safe metadata context for the watsonx prompt.
    Uses ONLY allow-listed fields already stored in the SaaS database.
    No raw logs, secrets, or sensitive data is included.
    """
    from ..models.incident import Incident
    from ..models.alert import Alert
    from ..models.collector import Collector
    from ..models.telemetry import Metric
    from datetime import datetime, timezone, timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    cutoff_str = cutoff.isoformat()

    # Recent metrics (last 10 per category, only allowed fields)
    metrics = (
        db.query(Metric)
        .filter(Metric.tenant_id == tenant_id, Metric.event_time >= cutoff_str)
        .order_by(Metric.event_time.desc())
        .limit(20)
        .all()
    )
    metrics_lines = [
        f"  {m.source_id} | {m.category} | {m.value:.1f} | {m.event_time[:16]}"
        for m in metrics
    ]

    # Recent open incidents (last 5)
    incidents = (
        db.query(Incident)
        .filter(Incident.tenant_id == tenant_id, Incident.status == "open")
        .order_by(Incident.created_at.desc())
        .limit(5)
        .all()
    )
    incident_lines = [
        f"  [{i.severity.upper()}] {i.title} (created {str(i.created_at)[:16]})"
        for i in incidents
    ]

    # Recent alerts (last 5)
    alerts = (
        db.query(Alert)
        .filter(Alert.tenant_id == tenant_id)
        .order_by(Alert.created_at.desc())
        .limit(5)
        .all()
    )
    alert_lines = [
        f"  [{a.severity.upper()}] {a.source_id} | {a.metric_category} | {a.message[:100]}"
        for a in alerts
    ]

    # Collector status
    collectors = db.query(Collector).filter(Collector.tenant_id == tenant_id).all()
    collector_lines = [
        f"  {c.name} | {c.status} | last seen {str(c.last_heartbeat_at)[:16] if c.last_heartbeat_at else 'unknown'}"
        for c in collectors
    ]

    nl = "\n"
    metrics_block = nl.join(metrics_lines) if metrics_lines else "  No metrics in the last hour."
    incidents_block = nl.join(incident_lines) if incident_lines else "  No open incidents."
    alerts_block = nl.join(alert_lines) if alert_lines else "  No recent alerts."
    collectors_block = nl.join(collector_lines) if collector_lines else "  No collectors registered."

    context = (
        "You are SentinelOps AI, a helpful AIOps assistant. "
        "You ONLY answer questions using the metadata below.\n"
        "You MUST NOT guess, invent, or hallucinate facts not present in the metadata.\n"
        "If the metadata does not contain enough information to answer, say so clearly.\n\n"
        "=== RECENT METRICS (last 1 hour) ===\n"
        f"{metrics_block}\n\n"
        "=== OPEN INCIDENTS ===\n"
        f"{incidents_block}\n\n"
        "=== RECENT ALERTS ===\n"
        f"{alerts_block}\n\n"
        "=== COLLECTOR STATUS ===\n"
        f"{collectors_block}\n\n"
        "=== OPERATOR QUESTION ===\n"
        f"{question}\n\n"
        "=== YOUR ANSWER (reference specific metadata values in your response) ==="
    )
    return context


def ask_sentinel_ai(
    db: Session,
    tenant_id: str,
    question: str,
) -> dict:
    """
    Answer an operator question using watsonx AI with metadata context.

    Returns a dict with:
      - answer: str (the AI response)
      - source: "watsonx" | "rule-based" (which system answered)
      - context_used: list of metadata categories included in the prompt
      - warning: str | None (any important caveats)

    Falls back to the rule-based recommender if watsonx is unavailable.
    """
    if not settings.ibm_watsonx_api_key or not settings.ibm_watsonx_project_id:
        return _rule_based_fallback(db, tenant_id, question)

    iam_token = _get_iam_token()
    if not iam_token:
        return _rule_based_fallback(db, tenant_id, question)

    context = _build_context(db, tenant_id, question)

    endpoint = settings.ibm_watsonx_endpoint
    if not endpoint:
        return _rule_based_fallback(db, tenant_id, question)

    payload = {
        "model_id": _WATSONX_MODEL,
        "project_id": settings.ibm_watsonx_project_id,
        "messages": [
            {
                "role": "user",
                "content": context,
            }
        ],
        "parameters": {
            "max_new_tokens": _MAX_NEW_TOKENS,
            "temperature": 0.1,   # Low temperature = more deterministic, fact-based
        },
    }

    try:
        resp = requests.post(
            endpoint,
            json=payload,
            headers={
                "Authorization": f"Bearer {iam_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        # Extract answer from watsonx response structure
        choices = data.get("choices", [])
        if choices:
            answer = choices[0].get("message", {}).get("content", "").strip()
        else:
            # Try the results structure used by some watsonx model versions
            results = data.get("results", [])
            answer = results[0].get("generated_text", "").strip() if results else ""

        if not answer:
            return _rule_based_fallback(db, tenant_id, question)

        return {
            "answer": answer,
            "source": "watsonx",
            "model": _WATSONX_MODEL,
            "context_used": ["metrics", "incidents", "alerts", "collectors"],
            "warning": (
                "This answer is based on approved metadata only. "
                "Raw logs, secrets, and sensitive data were NOT sent to IBM watsonx."
            ),
        }

    except requests.exceptions.Timeout:
        log.warning("[WATSONX] Request timed out — using rule-based fallback")
        return _rule_based_fallback(db, tenant_id, question, timeout=True)
    except requests.exceptions.HTTPError as e:
        log.error(f"[WATSONX] HTTP error {e.response.status_code}")
        return _rule_based_fallback(db, tenant_id, question)
    except Exception as e:
        log.error(f"[WATSONX] Unexpected error: {e}")
        return _rule_based_fallback(db, tenant_id, question)


def _rule_based_fallback(
    db: Session,
    tenant_id: str,
    question: str,
    timeout: bool = False,
) -> dict:
    """
    Deterministic metadata-based fallback for when watsonx is unavailable.
    Answers common operational questions using simple keyword matching.
    Does NOT fabricate answers — if metadata is insufficient, says so clearly.
    """
    from ..models.incident import Incident
    from ..models.alert import Alert
    from ..models.collector import Collector
    from ..models.telemetry import Metric
    from datetime import datetime, timezone, timedelta

    q = question.lower()
    answer = ""

    # "Which server has highest CPU?"
    if "cpu" in q and ("highest" in q or "most" in q or "top" in q):
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        metrics = (
            db.query(Metric)
            .filter(Metric.tenant_id == tenant_id, Metric.category == "cpu",
                    Metric.event_time >= cutoff)
            .order_by(Metric.value.desc())
            .limit(1)
            .first()
        )
        if metrics:
            answer = (
                f"Based on the last hour of data, **{metrics.source_id}** has the "
                f"highest CPU usage at **{metrics.value:.1f}%** "
                f"(recorded at {metrics.event_time[:16]} UTC)."
            )
        else:
            answer = "No CPU metrics available in the last hour."

    # "What incidents occurred?"
    elif "incident" in q:
        incidents = (
            db.query(Incident)
            .filter(Incident.tenant_id == tenant_id)
            .order_by(Incident.created_at.desc())
            .limit(5)
            .all()
        )
        if incidents:
            lines = [
                f"- [{i.severity.upper()}] {i.title} ({i.status}) — {str(i.created_at)[:16]} UTC"
                for i in incidents
            ]
            answer = "Recent incidents:\n" + "\n".join(lines)
        else:
            answer = "No incidents found."

    # "Why is X unhealthy?" or "why unhealthy"
    elif "unhealthy" in q or "poor" in q:
        alerts = (
            db.query(Alert)
            .filter(Alert.tenant_id == tenant_id, Alert.severity.in_(["critical", "warning"]))
            .order_by(Alert.created_at.desc())
            .limit(3)
            .all()
        )
        if alerts:
            lines = [
                f"- {a.source_id} | {a.metric_category}: {a.message[:120]}"
                for a in alerts
            ]
            answer = "Recent high-severity alerts that may explain unhealthy status:\n" + "\n".join(lines)
        else:
            answer = "No recent high-severity alerts found. Check collector connectivity."

    # "Collector" questions
    elif "collector" in q:
        collectors = db.query(Collector).filter(Collector.tenant_id == tenant_id).all()
        if collectors:
            lines = [
                f"- {c.name}: {c.status} (last heartbeat: {str(c.last_heartbeat_at)[:16] if c.last_heartbeat_at else 'unknown'} UTC)"
                for c in collectors
            ]
            answer = "Collector status:\n" + "\n".join(lines)
        else:
            answer = "No collectors registered for your tenant."

    else:
        answer = (
            "I can answer questions about: highest CPU/memory usage, recent incidents, "
            "unhealthy servers, collector status, and recent alerts. "
            "Please rephrase your question using these topics."
        )

    source_note = " (watsonx timed out — using local rule-based engine)" if timeout else ""

    return {
        "answer": answer,
        "source": f"rule-based{source_note}",
        "model": "deterministic-rule-engine",
        "context_used": ["metrics", "incidents", "alerts", "collectors"],
        "warning": (
            "This answer uses a local rule-based engine. "
            "No data was sent to any external service."
        ),
    }
