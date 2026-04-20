#!/usr/bin/env python3
"""
sentinel_os/__main__.py
------------------------
CLI entry point: python -m sentinel_os [options]

Examples:
    python -m sentinel_os
    python -m sentinel_os --scheduler edf --seed 42 --steps 200
    python -m sentinel_os --scheduler hybrid --gantt --no-ai
    python -m sentinel_os --compare        # run all schedulers & compare
"""

import argparse
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sentinel_os.core.system_simulator import SystemSimulator
from sentinel_os.monitoring.visualizer import generate_gantt, generate_resource_plot


def main():
    parser = argparse.ArgumentParser(
        prog="sentinelosus",
        description="SentinelOS — AI-Advised Microkernel for AUVs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--scheduler", choices=["hybrid", "edf", "priority", "rr"],
        default="hybrid", help="Scheduling algorithm to use"
    )
    parser.add_argument("--seed",  type=int, default=42,  help="Random seed")
    parser.add_argument("--steps", type=int, default=300, help="Simulation ticks")
    parser.add_argument("--no-ai", action="store_true",   help="Disable AI advisor")
    parser.add_argument("--gantt", action="store_true",   help="Generate Gantt chart PNG")
    parser.add_argument("--resource-plot", action="store_true", help="Generate resource plot")
    parser.add_argument("--export", type=str, default=None,
                        help="Export KPI results to JSON file")
    parser.add_argument("--compare", action="store_true",
                        help="Run all schedulers and print comparison table")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Suppress per-step log output")
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="Launch the interactive SentinelOS shell")

    # If no arguments besides -i or --scheduler are provided, default to shell
    # Checking sys.argv specifically to see if any execution flags were passed
    exec_flags = {"--steps", "--seed", "--compare", "--gantt", "--resource-plot", "--export"}
    is_direct_exec = any(arg in sys.argv for arg in exec_flags)

    args = parser.parse_args()

    if args.compare:
        # Delegate to the benchmark script
        from scripts.compare_schedulers import run_benchmark, print_comparison_table
        results = run_benchmark(seed=args.seed, steps=args.steps,
                                enable_ai=not args.no_ai)
        print_comparison_table(results)
        return

    sim = SystemSimulator(
        scheduler_policy=args.scheduler,
        enable_ai=not args.no_ai,
        seed=args.seed,
        max_time=args.steps,
        verbose=not args.quiet,
    )

    # Launch Shell if requested OR if no direct execution params given
    if args.interactive or not is_direct_exec:
        from sentinel_os.core.shell import SentinelShell
        shell = SentinelShell(sim)
        shell.run()
        return

    sim.initialize()
    result = sim.run()

    if args.export:
        sim.metrics.export_json(args.export)


    if args.gantt:
        out = f"gantt_{args.scheduler}.png"
        generate_gantt(
            sim.metrics.records,
            output_path=out,
            title=f"SentinelOS — {args.scheduler.upper()} Scheduler Gantt Chart",
        )

    if args.resource_plot:
        out = f"resources_{args.scheduler}.png"
        generate_resource_plot(
            sim.metrics.records,
            output_path=out,
            title=f"SentinelOS — Resource Utilization ({args.scheduler.upper()})",
        )


if __name__ == "__main__":
    main()
