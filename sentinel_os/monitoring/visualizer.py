"""
sentinel_os/monitoring/visualizer.py
--------------------------------------
Gantt chart and metrics plot generator for SentinelOS.

Produces:
  1. Gantt chart  — task execution timeline with colour-coded states
  2. Metrics bar  — side-by-side scheduler KPI comparison
  3. Resource plot — memory & battery depletion over time

Requires: matplotlib (pip install matplotlib)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pathlib import Path

# Defer import so the rest of the project works without matplotlib
try:
    import matplotlib
    matplotlib.use("Agg")   # non-interactive backend (safe on all platforms)
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    _HAS_MATPLOTLIB = True
except ImportError:
    _HAS_MATPLOTLIB = False


# Colour scheme for task states
STATE_COLORS: Dict[str, str] = {
    "RUNNING":    "#4CAF50",   # green
    "BLOCKED":    "#FFC107",   # amber
    "FAULT":      "#F44336",   # red
    "TERMINATED": "#9E9E9E",   # grey
    "READY":      "#2196F3",   # blue (edge case: shown as ready burst)
    "DEADLINE_MISS": "#FF5722", # deep orange
}


def _require_matplotlib():
    if not _HAS_MATPLOTLIB:
        raise ImportError(
            "matplotlib is required for visualization.\n"
            "Install it with:  pip install matplotlib"
        )


# ------------------------------------------------------------------ #
#  Gantt Chart                                                         #
# ------------------------------------------------------------------ #

def generate_gantt(
    records: List[Dict],
    output_path: str = "gantt_chart.png",
    title: str = "SentinelOS — Task Execution Timeline",
    max_tasks: int = 20,
) -> str:
    """
    Generate a Gantt chart from simulation step records.

    Parameters
    ----------
    records : list of step dicts from Metrics.records
    output_path : PNG file path to write
    title : chart title
    max_tasks : limit displayed tasks (avoids visual clutter)

    Returns the output_path string.
    """
    _require_matplotlib()

    # Collect per-task execution segments: {tid: [(start, end, state, type)]}
    task_segments: Dict[Any, List] = {}
    task_types: Dict[Any, str] = {}

    prev_tid = None
    seg_start = 0
    prev_state = None

    for step in records:
        t = step["time"]
        if step.get("task_running"):
            tid = step["task_id"]
            state = step.get("task_state", "RUNNING")
            ttype = step.get("task_type", "?")

            if tid not in task_segments:
                task_segments[tid] = []
                task_types[tid] = ttype

            if tid != prev_tid or state != prev_state:
                # close previous segment
                if prev_tid is not None and task_segments.get(prev_tid):
                    task_segments[prev_tid].append((seg_start, t, prev_state))
                seg_start = t
                prev_tid = tid
                prev_state = state
        else:
            if prev_tid is not None:
                task_segments.setdefault(prev_tid, []).append((seg_start, step["time"], prev_state))
                prev_tid = None
                prev_state = None

    # close final segment
    if prev_tid is not None and records:
        last_t = records[-1]["time"]
        task_segments.setdefault(prev_tid, []).append((seg_start, last_t + 1, prev_state))

    if not task_segments:
        print("  ⚠ No task data to plot.")
        return output_path

    # Limit to max_tasks most active
    sorted_tids = sorted(
        task_segments.keys(),
        key=lambda k: sum(e - s for s, e, _ in task_segments[k]),
        reverse=True,
    )[:max_tasks]

    fig, ax = plt.subplots(figsize=(16, max(4, len(sorted_tids) * 0.5 + 2)))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    y_labels = []
    for idx, tid in enumerate(sorted_tids):
        y = idx
        ttype = task_types.get(tid, "?")
        y_labels.append(f"Task {tid}\n{ttype}")

        for seg_start, seg_end, state in task_segments[tid]:
            color = STATE_COLORS.get(state, "#607D8B")
            width = max(seg_end - seg_start, 0.5)
            ax.barh(
                y, width, left=seg_start,
                color=color, edgecolor="#ffffff22",
                linewidth=0.3, height=0.6,
            )

    ax.set_yticks(range(len(sorted_tids)))
    ax.set_yticklabels(y_labels, fontsize=7, color="white")
    ax.set_xlabel("Simulation Time (ticks)", color="white", fontsize=10)
    ax.set_title(title, color="white", fontsize=13, fontweight="bold", pad=12)
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_edgecolor("#444")

    # Legend
    legend_patches = [
        mpatches.Patch(color=c, label=s) for s, c in STATE_COLORS.items()
    ]
    ax.legend(
        handles=legend_patches, loc="upper right",
        fontsize=7, framealpha=0.3,
        labelcolor="white", facecolor="#1a1a2e",
    )

    total_time = records[-1]["time"] if records else 1
    ax.set_xlim(0, total_time + 1)
    ax.invert_yaxis()

    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  ✅ Gantt chart saved → {output_path}")
    return output_path


# ------------------------------------------------------------------ #
#  Scheduler Comparison Bar Chart                                      #
# ------------------------------------------------------------------ #

def generate_comparison_chart(
    results: List[Dict],
    output_path: str = "scheduler_comparison.png",
) -> str:
    """
    Side-by-side bar chart comparing KPIs across scheduler runs.

    Parameters
    ----------
    results : list of dicts returned by Metrics.to_dict()
    output_path : PNG file path
    """
    _require_matplotlib()

    metrics_to_plot = [
        ("task_completion_rate",   "Completion Rate", True),
        ("deadline_miss_rate",     "Deadline Miss Rate", False),
        ("cpu_utilization",        "CPU Utilization", True),
        ("throughput",             "Throughput (tasks/step)", True),
        ("average_waiting_time",   "Avg Waiting Time (ticks)", False),
        ("average_turnaround_time","Avg Turnaround (ticks)", False),
    ]

    schedulers = [r["scheduler"] for r in results]
    n_metrics = len(metrics_to_plot)
    n_scheds  = len(results)

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    fig.patch.set_facecolor("#1a1a2e")
    axes_flat = axes.flatten()

    palette = ["#4CAF50", "#2196F3", "#FF9800", "#E91E63"]

    for ax_idx, (key, label, higher_is_better) in enumerate(metrics_to_plot):
        ax = axes_flat[ax_idx]
        ax.set_facecolor("#16213e")

        values = [r.get(key, 0) or 0 for r in results]
        best_val = max(values) if higher_is_better else min(values)

        bars = ax.bar(
            schedulers, values,
            color=[palette[i % len(palette)] for i in range(n_scheds)],
            edgecolor="#ffffff22", linewidth=0.5,
        )

        # Highlight winner
        for bar, val in zip(bars, values):
            if val == best_val:
                bar.set_edgecolor("gold")
                bar.set_linewidth(2)

        ax.set_title(label, color="white", fontsize=9, fontweight="bold")
        ax.set_ylabel("" , color="white")
        ax.tick_params(colors="white", labelsize=8)
        ax.set_facecolor("#16213e")
        for spine in ax.spines.values():
            spine.set_edgecolor("#444")

        # Value labels on bars
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(values) * 0.02,
                f"{val:.3f}", ha="center", va="bottom",
                color="white", fontsize=7,
            )

    fig.suptitle("SentinelOS — Scheduler Benchmark Comparison",
                 color="white", fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  ✅ Comparison chart saved → {output_path}")
    return output_path


# ------------------------------------------------------------------ #
#  Resource Depletion Plot                                             #
# ------------------------------------------------------------------ #

def generate_resource_plot(
    records: List[Dict],
    output_path: str = "resource_plot.png",
    title: str = "SentinelOS — Resource Utilization Over Time",
) -> str:
    """Line plot of memory availability and battery level over simulation time."""
    _require_matplotlib()

    times    = [r["time"]    for r in records]
    memory   = [r.get("memory", 0)  for r in records]
    battery  = [r.get("battery", 0) for r in records]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 6), sharex=True)
    fig.patch.set_facecolor("#1a1a2e")

    for ax, values, label, color in [
        (ax1, memory,  "Available Memory (units)", "#4CAF50"),
        (ax2, battery, "Battery Level",            "#FFC107"),
    ]:
        ax.set_facecolor("#16213e")
        ax.plot(times, values, color=color, linewidth=1.2, alpha=0.9)
        ax.fill_between(times, values, alpha=0.15, color=color)
        ax.set_ylabel(label, color="white", fontsize=9)
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_edgecolor("#444")

    ax2.set_xlabel("Simulation Time (ticks)", color="white", fontsize=10)
    fig.suptitle(title, color="white", fontsize=12, fontweight="bold")
    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  ✅ Resource plot saved → {output_path}")
    return output_path
