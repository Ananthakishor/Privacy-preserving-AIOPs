"""
collector/sources/psutil_source.py
Collects real infrastructure metrics from the local machine using psutil.

psutil is a cross-platform library that reads CPU, memory, disk, and network
statistics directly from the operating system. We use it here to collect
the metrics that ARE permitted to leave the environment (values, not logs).

The raw psutil dict is processed further by the pipeline before transmission.
"""
import psutil
import time
from datetime import datetime, timezone


def collect_metrics() -> dict:
    """
    Collect current system metrics using psutil.

    Returns a raw dict that STILL contains full system data.
    The pipeline (normalizer → redactor → allowlist) will process this
    before any data leaves the collector.

    This raw dict is stored locally only — never sent to SaaS directly.
    """
    # Simulate a dummy secret to prove redaction works (for demo purposes)
    # In production, real secrets might appear in environment vars or config files
    # that are accidentally included — the redactor catches these
    dummy_secret = "password=SuperSecret123"  # This will be redacted

    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/") if not _is_windows() else psutil.disk_usage("C:\\")
    net_io = psutil.net_io_counters()

    raw = {
        # Permitted metrics (will pass through allowlist)
        "cpu_percent": cpu,
        "memory_percent": mem.percent,
        "memory_total_gb": round(mem.total / (1024**3), 2),
        "memory_used_gb": round(mem.used / (1024**3), 2),
        "disk_percent": disk.percent,
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "disk_used_gb": round(disk.used / (1024**3), 2),
        "net_bytes_sent": net_io.bytes_sent,
        "net_bytes_recv": net_io.bytes_recv,
        "net_packets_sent": net_io.packets_sent,
        "net_packets_recv": net_io.packets_recv,
        "net_errin": net_io.errin,
        "net_errout": net_io.errout,

        # Simulated network metrics (psutil doesn't provide latency)
        "simulated_latency_ms": _simulate_latency(),
        "simulated_packet_loss_pct": _simulate_packet_loss(),

        # This is a SENSITIVE field — demonstrates that secrets are redacted
        # In a real environment, this could be an accidentally leaked env var
        "raw_config_snippet": dummy_secret,

        # Metadata
        "hostname": "collector-host-01",  # Will be replaced with pseudonymous source_id
        "collection_timestamp": datetime.now(timezone.utc).isoformat(),
        "source_timezone": "UTC",
    }
    return raw


def _is_windows() -> bool:
    import platform
    return platform.system() == "Windows"


def _simulate_latency() -> float:
    """Simulate network latency (psutil doesn't measure this)."""
    import random
    # Normal: 10-50ms, occasionally spikes to 200ms
    base = random.uniform(10, 50)
    if random.random() < 0.05:  # 5% chance of spike
        base *= random.uniform(4, 10)
    return round(base, 2)


def _simulate_packet_loss() -> float:
    """Simulate packet loss percentage."""
    import random
    if random.random() < 0.03:  # 3% chance of packet loss
        return round(random.uniform(0.5, 5.0), 2)
    return 0.0
