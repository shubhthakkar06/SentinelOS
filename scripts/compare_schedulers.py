#!/usr/bin/env python3
"""
scripts/compare_schedulers.py
-------------------------------
Benchmark all four SentinelOS schedulers on identical workloads and
produce a side-by-side comparison table + PNG chart.

Usage:
    python scripts/compare_schedulers.py
    python scripts/compare_schedulers.py --seed 99 --steps 400 --output results/
    python scripts/compare_schedulers.py --no-ai        # disable AI advisor

This is the single script that turns "I made a scheduler" into
"I benchmarked and compared 4 scheduling algorithms."
"""

import argparse
import json
import sys
import os
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from sentinel_os.core.system_simulator import SystemSimulator
from sentinel_os.monitoring.visualizer import generate_comparison_chart


SCHEDULERS = ["hybrid", "edf", "priority", "rr"]

SCHEDULER_LABELS = {
    "hybrid":   "Hybrid (AI-Advised)",
    "edf":      "EDF",
    "priority": "Static Priority",
    "rr":       "Round Robin",
}


def run_benchmark(
    seed: int = 42,
    steps: int = 300,
    enable_ai: bool = True,
    output_dir: str = "results",
) -> list[dict]:
    """Run all schedulers with the same seed and return their KPI dicts."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    all_results = []

    print(f"\n{'═'*60}")
    print(f"  SentinelOS Scheduler Benchmark")
    print(f"  Seed: {seed}  |  Steps: {steps}  |  AI: {enable_ai}")
    print(f"{'═'*60}\n")

    for sched in SCHEDULERS:
        print(f"▶  Running [{SCHEDULER_LABELS[sched]}] ...")
        sim = SystemSimulator(
            scheduler_policy=sched,
            enable_ai=enable_ai,
            seed=seed,
            max_time=steps,
            verbose=False,   # suppress per-step noise during benchmark
        )
        sim.initialize()
        result = sim.run()

        # Save individual JSON
        json_path = os.path.join(output_dir, f"{sched}_results.json")
        with open(json_path, "w") as f:
            json.dump(result, f, indent=2)

        all_results.append(result)
        print(f"   ✓ Done  (completion={result['task_completion_rate']:.1%}, "
              f"deadline_misses={result['deadline_miss_rate']:.1%})\n")

    return all_results


def print_comparison_table(results: list[dict]):
    """Print a rich ASCII comparison table."""
    metrics = [
        ("task_completion_rate",    "Completion Rate",        True,  ".1%"),
        ("deadline_miss_rate",      "Deadline Miss Rate",     False, ".1%"),
        ("cpu_utilization",         "CPU Utilization",        True,  ".1%"),
        ("throughput",              "Throughput (tasks/step)", True, ".5f"),
        ("average_waiting_time",    "Avg Wait (ticks)",       False, ".2f"),
        ("average_turnaround_time", "Avg Turnaround (ticks)", False, ".2f"),
        ("context_switches",        "Context Switches",       False, "d"),
        ("total_faults",            "Total Faults",           False, "d"),
        ("energy_consumed",         "Energy Consumed",        False, ".2f"),
        ("ai_interventions",        "AI Interventions",       None,  "d"),
    ]

    col_w = 22
    header = f"{'Metric':<28}" + "".join(
        f"{SCHEDULER_LABELS.get(r['scheduler'], r['scheduler']):<{col_w}}"
        for r in results
    )
    print("\n" + "═" * len(header))
    print("  BENCHMARK RESULTS")
    print("═" * len(header))
    print(header)
    print("─" * len(header))

    for key, label, higher_is_better, fmt in metrics:
        values = [r.get(key, 0) or 0 for r in results]

        if higher_is_better is True:
            best_val = max(values)
        elif higher_is_better is False:
            best_val = min(values)
        else:
            best_val = None   # neutral metric — no winner highlight

        row = f"  {label:<26}"
        for val in values:
            cell = format(val, fmt)
            # ★ mark the winner
            marker = " ★" if (best_val is not None and val == best_val) else "  "
            row += f"{cell + marker:<{col_w}}"
        print(row)

    print("═" * len(header))
    print("  ★ = best value for that metric\n")


def main():
    parser = argparse.ArgumentParser(
        description="SentinelOS Scheduler Benchmark",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--seed",   type=int, default=42,    help="Random seed")
    parser.add_argument("--steps",  type=int, default=300,   help="Simulation steps")
    parser.add_argument("--output", type=str, default="results", help="Output directory")
    parser.add_argument("--no-ai",  action="store_true",     help="Disable AI advisor")
    parser.add_argument("--no-chart", action="store_true",   help="Skip chart generation")
    args = parser.parse_args()

    results = run_benchmark(
        seed=args.seed,
        steps=args.steps,
        enable_ai=not args.no_ai,
        output_dir=args.output,
    )

    print_comparison_table(results)

    # Save combined JSON
    combined_path = os.path.join(args.output, "benchmark_summary.json")
    with open(combined_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  📄 Full results → {combined_path}")

    # Generate comparison chart
    if not args.no_chart:
        try:
            chart_path = os.path.join(args.output, "scheduler_comparison.png")
            generate_comparison_chart(results, output_path=chart_path)
        except ImportError as e:
            print(f"  ⚠ Chart skipped (matplotlib not installed): {e}")


if __name__ == "__main__":
    main()
