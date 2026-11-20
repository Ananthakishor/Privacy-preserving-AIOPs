"""
collector/collector.py
Main collector entry point.

This is what runs in the customer environment (Tier 1).
It orchestrates the full privacy pipeline:
  1. Collect metrics via psutil
  2. Normalize to internal format
  3. Redact secrets
  4. Apply allow-list
  5. Log to egress proof file
  6. Deliver to SaaS backend
  7. Buffer on failure, retry on reconnect
  8. Send heartbeat every 15 seconds

Run: python collector/collector.py
     OR: python -m collector.collector (from project root)
"""
import sys
import os
import time
import threading
import logging
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collector.config import config, env_file
from collector.sources.psutil_source import collect_metrics
from collector.sources.security_source import collect_security_signals
from collector.pipeline.normalizer import normalize_metrics
from collector.pipeline.redactor import redact_event
from collector.pipeline.allowlist import apply_allowlist
from collector.transport.sender import send_payload, retry_pending, send_heartbeat, confirm_registration
from collector.buffer.queue import init_buffer, count_pending

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [COLLECTOR] %(levelname)s: %(message)s"
)
log = logging.getLogger(__name__)

COLLECTOR_ID = config.COLLECTOR_ID


def run_collection_cycle():
    """
    One complete collection cycle:
    raw metrics → normalize → redact → allowlist → send
    """
    try:
        # Step 1: Collect raw metrics (stays local)
        raw_infra = collect_metrics()
        raw_security = collect_security_signals()

        # Preserve the infra data_source tag before merging security signals.
        # Security source may have a different data_source (e.g. "simulated" when
        # wevtutil is unavailable) — we don't want it to overwrite the "live" tag
        # for all infrastructure metrics.
        infra_data_source = raw_infra.get("data_source", "live")

        # Merge security signals into infra raw record
        raw_infra.update(raw_security)

        # Restore the infra data_source for infra metrics; security events
        # will use their own data_source (set in normalizer from the security raw dict)
        raw_infra["data_source"] = infra_data_source
        raw_infra["_security_data_source"] = raw_security.get("data_source", "live")

        # Step 2: Normalize — convert to list of metric events
        events = normalize_metrics(raw_infra, collector_id=COLLECTOR_ID)

        # Step 3-4: For each event, apply redaction then allow-list
        for raw_event in events:
            # Redact — scan for secret patterns
            redacted = redact_event(raw_event)

            # Apply allow-list — keep ONLY permitted fields
            approved = apply_allowlist(redacted)

            # Step 5-7: Send the approved payload
            success = send_payload(approved)
            if success:
                log.info(f"[SENT] {approved['metric_category']}={approved['metric_value']} "
                         f"source={approved['source_id']} event_id={approved['event_id'][:8]}...")
            else:
                log.warning(f"[BUFFERED] {approved['metric_category']}={approved['metric_value']} "
                            f"(backend unreachable, {count_pending()} pending)")

    except Exception as e:
        log.error(f"Collection cycle error: {e}")


def run_heartbeat_loop():
    """Background thread: send heartbeat to SaaS every 15 seconds."""
    last_sent = 0
    while True:
        now = time.time()
        if now - last_sent >= config.HEARTBEAT_INTERVAL_SECONDS:
            try:
                import psutil
                cpu = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory().percent
            except Exception:
                cpu, mem = 0.0, 0.0

            acknowledged = send_heartbeat(
                collector_id=COLLECTOR_ID,
                cpu_pct=cpu,
                mem_pct=mem,
                buffered_count=count_pending(),
            )
            if acknowledged:
                log.info(f"[HEARTBEAT] cpu={cpu:.1f}% mem={mem:.1f}% buffered={count_pending()}")
            else:
                log.warning("Heartbeat was not acknowledged")
            last_sent = now
        time.sleep(1)


def run_retry_loop():
    """Background thread: retry buffered payloads every 30 seconds."""
    while True:
        time.sleep(30)
        pending = count_pending()
        if pending > 0:
            log.info(f"[RETRY] Attempting to deliver {pending} buffered payloads...")
            retry_pending()


def main():
    log.info("SentinelOps AI Collector starting...")
    log.info(f"  Tenant: {config.COLLECTOR_TENANT_ID}")
    log.info(f"  Source: {config.COLLECTOR_SOURCE_ID}")
    log.info(f"  SaaS endpoint: {config.SAAS_INGEST_URL}")
    log.info(f"  Egress proof log: {config.EGRESS_LOG_PATH}")

    # Initialize local buffer
    init_buffer()
    log.info("[OK] Local buffer initialized")

    if env_file:
        # Registration confirms the identity provisioned by the administrator.
        # Offline starts can still collect and buffer under that identity.
        confirm_registration()

    # Start heartbeat thread
    hb_thread = threading.Thread(target=run_heartbeat_loop, daemon=True)
    hb_thread.start()

    # Start retry thread
    retry_thread = threading.Thread(target=run_retry_loop, daemon=True)
    retry_thread.start()

    log.info(f"Collecting metrics every {config.EMIT_INTERVAL_SECONDS} seconds. Press Ctrl+C to stop.")

    # Main collection loop
    while True:
        run_collection_cycle()
        time.sleep(config.EMIT_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
