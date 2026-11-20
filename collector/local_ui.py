"""
collector/local_ui.py
Local-only web UI for viewing the egress proof log and raw telemetry.

THIS SERVER RUNS ON PORT 8001 — ACCESSIBLE ONLY LOCALLY.
It must NEVER be exposed to the internet or to the SaaS backend.

The local UI shows:
- Raw collected metrics (including dummy secrets — to prove they stay local)
- The egress proof log (what was actually sent after redaction + allow-listing)
- Side-by-side comparison showing the privacy pipeline in action

Run: python collector/local_ui.py
Access: http://localhost:8001
"""
import sys
import os
import json
import psutil
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collector.config import config
from collector.egress_proof.logger import read_egress_log
from collector.buffer.queue import count_pending, count_delivered
from collector.sources.security_source import collect_security_signals

app = FastAPI(
    title="SentinelOps AI — Local Collector UI",
    description="LOCAL ONLY — Egress proof and raw telemetry viewer. Never expose to the internet.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Root — show a human-readable notice."""
    return {
        "service": "SentinelOps AI Local Collector UI",
        "warning": "LOCAL ONLY — Do not expose this service to the internet",
        "endpoints": {
            "/raw": "Current raw metrics (including sensitive fields)",
            "/egress-log": "Approved payloads sent to SaaS (last 50)",
            "/buffer-status": "Local queue statistics",
            "/compare": "Side-by-side raw vs approved payload comparison",
        }
    }


@app.get("/raw")
def get_raw_metrics():
    """
    Show the CURRENT raw collected metrics — including sensitive fields.
    This endpoint is LOCAL ONLY and proves that sensitive data stays here.
    """
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\" if os.name == "nt" else "/")
    sec = collect_security_signals()

    return {
        "_warning": "RAW DATA — LOCAL ONLY — This data never leaves this machine",
        "_note": "The 'raw_config_snippet' and '_raw_*' fields demonstrate that secrets are caught and redacted",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu_percent": cpu,
        "memory_percent": mem.percent,
        "memory_total_gb": round(mem.total / (1024**3), 2),
        "disk_percent": disk.percent,
        "simulated_latency_ms": 25.4,
        "raw_config_snippet": "password=SuperSecret123",  # DEMO: this never leaves
        "failed_login_count": sec.get("failed_login_count", 0),
        "_raw_usernames_attempted": sec.get("_raw_usernames_attempted", []),  # NEVER sent to SaaS
        "_raw_source_ips": sec.get("_raw_source_ips", []),  # NEVER sent to SaaS
    }


@app.get("/egress-log")
def get_egress_log(limit: int = 50):
    """Show the last N entries from the egress proof log."""
    entries = read_egress_log(last_n=limit)
    return {
        "count": len(entries),
        "entries": entries,
        "log_file": config.EGRESS_LOG_PATH,
    }


@app.get("/buffer-status")
def get_buffer_status():
    """Show local queue statistics."""
    return {
        "pending_payloads": count_pending(),
        "delivered_payloads": count_delivered(),
        "saas_endpoint": config.SAAS_INGEST_URL,
        "collector_id": config.COLLECTOR_SOURCE_ID,
        "tenant_id": config.COLLECTOR_TENANT_ID,
    }


@app.get("/compare")
def compare_raw_vs_approved():
    """
    Side-by-side demonstration of the privacy pipeline.
    Shows what the raw record contains vs what the approved payload contains.
    """
    from collector.sources.psutil_source import collect_metrics
    from collector.pipeline.normalizer import normalize_metrics
    from collector.pipeline.redactor import redact_event
    from collector.pipeline.allowlist import apply_allowlist, get_allowed_fields

    raw = collect_metrics()
    events = normalize_metrics(raw, collector_id="local-demo")
    if not events:
        return {"error": "No events collected"}

    first_event = events[0]
    redacted = redact_event(first_event)
    approved = apply_allowlist(redacted)

    return {
        "demonstration": "Privacy pipeline: raw → redacted → approved",
        "step_1_raw_fields": sorted(first_event.keys()),
        "step_1_raw_contains_secrets": any(
            k.startswith("_raw") or "secret" in k or "password" in str(v)
            for k, v in first_event.items()
        ),
        "step_2_redacted_fields": sorted(redacted.keys()),
        "step_3_approved_fields": sorted(approved.keys()),
        "allowed_field_list": get_allowed_fields(),
        "fields_dropped_count": len(first_event) - len(approved),
        "approved_payload_preview": approved,
    }


if __name__ == "__main__":
    print(f"Starting Local Collector UI on http://localhost:{config.LOCAL_UI_PORT}")
    print("WARNING: This UI is for LOCAL USE ONLY — do not expose to internet")
    uvicorn.run(app, host="127.0.0.1", port=config.LOCAL_UI_PORT)
