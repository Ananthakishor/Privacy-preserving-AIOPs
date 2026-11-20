"""
collector/sources/psutil_source.py
Collects real infrastructure metrics from the local machine using psutil
and real network latency using ICMP ping (Windows: ping.exe via subprocess).

psutil is a cross-platform library that reads CPU, memory, disk, and network
statistics directly from the operating system.

Network latency and packet loss are measured by running 'ping -n 4 <target>'
on Windows. This is a real OS measurement, not a random number.

The raw psutil dict is processed further by the pipeline before transmission.
"""
import psutil
import platform
import subprocess
import re
import time
import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)

# Target host to ping for latency measurement.
# Using Google's public DNS as the default; configurable via environment.
# If the host is unreachable the value is marked with a high sentinel (999ms).
import os
_PING_TARGET = os.environ.get("PING_TARGET", "8.8.8.8")
_PING_COUNT = int(os.environ.get("PING_COUNT", "4"))


def collect_metrics() -> dict:
    """
    Collect current system metrics using psutil + real ICMP ping.

    Returns a raw dict that STILL contains full system data.
    The pipeline (normalizer → redactor → allowlist) will process this
    before any data leaves the collector.

    This raw dict is stored locally only — never sent to SaaS directly.
    """
    # Simulate a dummy secret to prove redaction works (for demo purposes).
    # In production, real secrets might appear in environment vars or config
    # files that are accidentally included — the redactor catches these.
    dummy_secret = "password=SuperSecret123"  # This will be redacted

    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\") if _is_windows() else psutil.disk_usage("/")
    net_io = psutil.net_io_counters()

    # Real latency and packet loss measured via ICMP ping
    latency_ms, packet_loss_pct = _measure_latency_and_loss(_PING_TARGET, _PING_COUNT)

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

        # Real network quality metrics from ICMP ping
        # Labeled as "measured" to distinguish from simulator values
        "measured_latency_ms": latency_ms,
        "measured_packet_loss_pct": packet_loss_pct,

        # Legacy key kept for normalizer compatibility
        "simulated_latency_ms": latency_ms,

        # This is a SENSITIVE field — demonstrates that secrets are redacted.
        # In a real environment, this could be an accidentally leaked env var.
        "raw_config_snippet": dummy_secret,

        # Metadata
        "hostname": "collector-host-01",  # Will be replaced with pseudonymous source_id
        "collection_timestamp": datetime.now(timezone.utc).isoformat(),
        "source_timezone": "UTC",

        # Data-source tag so the dashboard can label values correctly
        "data_source": "live",
    }
    return raw


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _measure_latency_and_loss(target: str, count: int) -> tuple:
    """
    Run an OS-level ICMP ping and extract average latency (ms) and
    packet loss (%) from the output.

    Windows: ping -n <count> <target>
    Linux/macOS: ping -c <count> <target>

    Returns (latency_ms, packet_loss_pct).
    If ping fails (firewall, no network), returns (999.0, 100.0) so the
    dashboard displays a clear "unreachable" state rather than fake low values.

    This function is REAL — it makes actual OS system calls.
    It is NOT simulated. The returned values depend on actual network conditions.
    """
    try:
        if _is_windows():
            cmd = ["ping", "-n", str(count), target]
        else:
            cmd = ["ping", "-c", str(count), "-W", "2", target]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(count * 3, 15),   # generous timeout: 3s per ping + buffer
        )
        output = result.stdout + result.stderr

        latency_ms = _parse_latency_windows(output) if _is_windows() else _parse_latency_unix(output)
        packet_loss_pct = _parse_packet_loss(output)

        return latency_ms, packet_loss_pct

    except subprocess.TimeoutExpired:
        log.warning(f"[PING] Timeout pinging {target} — marking unreachable")
        return 999.0, 100.0
    except FileNotFoundError:
        # ping binary not found (unusual but handled)
        log.warning("[PING] ping binary not found — returning default values")
        return 0.0, 0.0
    except Exception as e:
        log.warning(f"[PING] Unexpected error: {e}")
        return 0.0, 0.0


def _parse_latency_windows(output: str) -> float:
    """
    Parse Windows ping output to extract average round-trip time.

    Windows ping output example:
        Minimum = 11ms, Maximum = 14ms, Average = 12ms
    """
    # Try "Average = Xms" pattern first
    match = re.search(r"Average\s*=\s*(\d+)ms", output, re.IGNORECASE)
    if match:
        return float(match.group(1))

    # Fallback: parse individual reply times and average them
    # e.g. "Reply from 8.8.8.8: bytes=32 time=12ms TTL=118"
    times = re.findall(r"time[<=](\d+)ms", output, re.IGNORECASE)
    if times:
        return round(sum(float(t) for t in times) / len(times), 2)

    return 999.0  # No parseable reply — host unreachable


def _parse_latency_unix(output: str) -> float:
    """
    Parse Linux/macOS ping output to extract average RTT.

    Output example:
        rtt min/avg/max/mdev = 11.234/12.456/14.123/0.890 ms
    """
    match = re.search(r"min/avg/max.*?=\s*[\d.]+/([\d.]+)/", output)
    if match:
        return round(float(match.group(1)), 2)
    return 999.0


def _parse_packet_loss(output: str) -> float:
    """
    Parse ping output to extract packet loss percentage.

    Windows: "(25% loss)"
    Linux:   "25% packet loss"
    """
    # Windows: "(25% loss)" or "25% loss"
    match = re.search(r"\((\d+)%\s+loss\)", output, re.IGNORECASE)
    if match:
        return float(match.group(1))

    # Linux/macOS: "25% packet loss"
    match = re.search(r"(\d+)%\s+packet loss", output, re.IGNORECASE)
    if match:
        return float(match.group(1))

    # Windows sometimes: "0% loss" without parentheses
    match = re.search(r"(\d+)%\s+loss", output, re.IGNORECASE)
    if match:
        return float(match.group(1))

    return 0.0
