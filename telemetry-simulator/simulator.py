"""
telemetry-simulator/simulator.py
Standalone telemetry scenario injector.

Usage:
  python simulator.py                   # Run normal scenario continuously
  python simulator.py --scenario cpu_spike
  python simulator.py --scenario correlated
  python simulator.py --scenario memory_spike
  python simulator.py --scenario latency_rise
  python simulator.py --scenario auth_failures
  python simulator.py --scenario duplicates
  python simulator.py --scenario out_of_order
  python simulator.py --scenario outage    # Simulate SaaS unavailability

The simulator sends approved metadata directly to the SaaS ingest endpoint,
bypassing the local collector — this is for DEMO/TEST purposes only.
In production evaluation, the organizer's official stream adapter is used.
"""
import sys
import os
import uuid
import json
import time
import argparse
import requests
import signal
import threading
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

SAAS_INGEST_URL = os.getenv("SAAS_INGEST_URL", "http://localhost:8000/api/v1/telemetry/ingest")
COLLECTOR_API_KEY = os.getenv("COLLECTOR_API_KEY", "collector-secret-key-cicada2026")
COLLECTOR_ID = "simulator-collector-01"
TENANT_ID = os.getenv("COLLECTOR_TENANT_ID", "tenant-alpha")
EMIT_INTERVAL = float(os.getenv("SIMULATOR_EMIT_INTERVAL_SECONDS", "5"))

_running = True
_outage_mode = False


def signal_handler(sig, frame):
    global _running
    print("\n[SIMULATOR] Stopping...")
    _running = False


signal.signal(signal.SIGINT, signal_handler)


def make_payload(source_id: str, category: str, value: float,
                 event_id: str = None, event_time: str = None) -> dict:
    """Create a compliant TelemetryIngestPayload."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "tenant_id": TENANT_ID,
        "source_id": source_id,
        "event_id": event_id or str(uuid.uuid4()),
        "utc_timestamp": now,
        "event_time": event_time or now,
        "source_timezone": "UTC",
        "metric_category": category,
        "metric_value": value,
        "severity": _classify_severity(category, value),
        "health_status": _classify_health(category, value),
        "alert_context": f"Simulated {category} reading",
        "collector_id": COLLECTOR_ID,
    }


def _classify_severity(category: str, value: float) -> str:
    thresholds = {"cpu": (75, 90), "memory": (80, 90), "disk": (80, 90), "network": (200, 500), "security": (5, 10)}
    warn, crit = thresholds.get(category, (70, 90))
    if value >= crit:
        return "critical"
    elif value >= warn:
        return "warning"
    return "info"


def _classify_health(category: str, value: float) -> str:
    thresholds = {"cpu": (60, 75, 90), "memory": (70, 80, 90), "network": (100, 200, 500)}
    good, fair, poor = thresholds.get(category, (60, 75, 90))
    if value >= poor:
        return "poor"
    elif value >= fair:
        return "fair"
    elif value >= good:
        return "good"
    return "excellent"


def send(payload: dict) -> str:
    """Send payload to SaaS. Returns status string."""
    if _outage_mode:
        return "SKIPPED (simulated outage)"
    headers = {"X-Collector-API-Key": COLLECTOR_API_KEY, "Content-Type": "application/json"}
    try:
        r = requests.post(SAAS_INGEST_URL, json=payload, headers=headers, timeout=5)
        if r.status_code == 409:
            return "DUPLICATE (409)"
        elif r.status_code in (200, 201):
            return "OK"
        else:
            return f"ERROR {r.status_code}"
    except Exception as e:
        return f"UNREACHABLE: {e}"


def _load_scenario(scenario_name: str):
    """Dynamically load a scenario module by name."""
    import importlib.util, os
    scenario_dir = os.path.join(os.path.dirname(__file__), "scenarios")
    module_path = os.path.join(scenario_dir, f"{scenario_name}.py")
    if not os.path.exists(module_path):
        module_path = os.path.join(scenario_dir, "normal.py")
    spec = importlib.util.spec_from_file_location(scenario_name, module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_scenario(scenario_name: str, ticks: int = 0):
    """Load and run a scenario module for one tick."""
    mod = _load_scenario(scenario_name)
    generate = mod.generate

    readings = generate(tick=ticks)
    results = []

    for reading in readings:
        # Support optional event_id and event_time override from scenario
        if len(reading) == 4:
            source_id, category, value, forced_event_id = reading
            payload = make_payload(source_id, category, value, event_id=forced_event_id)
        elif len(reading) == 5:
            source_id, category, value, forced_event_id, forced_time = reading
            payload = make_payload(source_id, category, value, event_id=forced_event_id, event_time=forced_time)
        else:
            source_id, category, value = reading
            payload = make_payload(source_id, category, value)

        status = send(payload)
        results.append(f"  {source_id}/{category}={value} -> {status}")

    return results


def outage_simulation():
    """Run outage simulation: 30s outage then reconnect."""
    global _outage_mode
    print("\n[OUTAGE] Simulating SaaS outage for 30 seconds...")
    _outage_mode = True
    time.sleep(30)
    _outage_mode = False
    print("[OUTAGE] Reconnected — retrying buffered payloads...")


def main():
    parser = argparse.ArgumentParser(description="SentinelOps AI Telemetry Simulator")
    parser.add_argument("--scenario", default="normal",
                        choices=["normal", "cpu_spike", "correlated", "memory_spike",
                                 "latency_rise", "auth_failures", "duplicates", "out_of_order", "outage"],
                        help="Telemetry scenario to run")
    parser.add_argument("--ticks", type=int, default=0,
                        help="Number of ticks to run (0 = infinite)")
    parser.add_argument("--interval", type=float, default=EMIT_INTERVAL,
                        help="Seconds between emissions")
    args = parser.parse_args()

    print(f"[SIMULATOR] Starting scenario: {args.scenario}")
    print(f"[SIMULATOR] Target: {SAAS_INGEST_URL}")
    print(f"[SIMULATOR] Tenant: {TENANT_ID}")
    print(f"[SIMULATOR] Interval: {args.interval}s")
    print("[SIMULATOR] Press Ctrl+C to stop\n")

    if args.scenario == "outage":
        outage_simulation()
        return

    tick = 0
    max_ticks = args.ticks if args.ticks > 0 else float("inf")

    while _running and tick < max_ticks:
        results = run_scenario(args.scenario, ticks=tick)
        print(f"[T={tick:04d}] {args.scenario}:")
        for r in results:
            print(r)
        tick += 1
        time.sleep(args.interval)

    print("[SIMULATOR] Done.")


if __name__ == "__main__":
    main()
