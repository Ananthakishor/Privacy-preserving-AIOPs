"""
scripts/demo_inject.py
Inject named demo scenarios for the hackathon demonstration.

Usage:
  python scripts/demo_inject.py --scenario cpu_spike
  python scripts/demo_inject.py --scenario correlated
  python scripts/demo_inject.py --scenario outage
  python scripts/demo_inject.py --scenario duplicates
  python scripts/demo_inject.py --scenario all  (runs the full demo flow)
"""
import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telemetry_simulator.simulator import run_scenario, outage_simulation, make_payload, send
import uuid
from datetime import datetime, timezone


def run_demo_scenario(scenario_name: str, ticks: int = 15, interval: float = 2.0):
    print(f"\n{'='*50}")
    print(f"DEMO: {scenario_name.upper().replace('_', ' ')}")
    print(f"{'='*50}")
    for tick in range(ticks):
        results = run_scenario(scenario_name, tick)
        for r in results:
            print(r)
        time.sleep(interval)
    print(f"[DONE] {scenario_name}")


def run_full_demo():
    print("\n[DEMO] Starting full SentinelOps AI demonstration...")
    print("[DEMO] Step 1: Normal operation (5 ticks)")
    run_demo_scenario("normal", ticks=5, interval=1)

    print("\n[DEMO] Step 2: CPU spike injection")
    run_demo_scenario("cpu_spike", ticks=10, interval=1)

    print("\n[DEMO] Step 3: Correlated resource saturation")
    run_demo_scenario("correlated", ticks=8, interval=1)

    print("\n[DEMO] Step 4: Outage simulation")
    outage_simulation()

    print("\n[DEMO] Step 5: Duplicate delivery test")
    run_demo_scenario("duplicates", ticks=4, interval=1)

    print("\n[DEMO] COMPLETE — Check dashboard at http://localhost:5173")


def main():
    parser = argparse.ArgumentParser(description="SentinelOps AI Demo Injector")
    parser.add_argument("--scenario", default="normal",
                        choices=["normal", "cpu_spike", "correlated", "memory_spike",
                                 "latency_rise", "auth_failures", "duplicates",
                                 "out_of_order", "outage", "all"],
                        help="Demo scenario to inject")
    parser.add_argument("--ticks", type=int, default=15)
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()

    if args.scenario == "all":
        run_full_demo()
    elif args.scenario == "outage":
        outage_simulation()
    else:
        run_demo_scenario(args.scenario, args.ticks, args.interval)


if __name__ == "__main__":
    main()
