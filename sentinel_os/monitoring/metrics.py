"""
sentinel_os/monitoring/metrics.py
----------------------------------
Comprehensive KPI engine for SentinelOS.

Tracks 10+ real-time metrics used by interviewers to evaluate
scheduling quality in real-time operating systems:
  - Deadline miss rate (core RTOS metric)
  - CPU utilization
  - Average waiting time (scheduling fairness)
  - Throughput (tasks completed per time unit)
  - Energy budget consumed
  - Context switch count
  - Fault rate by fault type
  - AI advisor intervention rate
  - Task completion rate (success vs fault-terminated)
"""

from typing import Dict, List, Optional
from collections import defaultdict
import json
import time as wallclock


class Metrics:
    """
    Collects comprehensive scheduling KPIs across an entire simulation run.
    Designed to be queried after a run to produce human-readable summaries
    or machine-readable JSON exports.
    """

    def __init__(self):
        # --- Step-level records ---
        self.records: List[Dict] = []          # one entry per simulation step
        self.faults: List[Dict] = []           # all recorded fault events

        # --- Task lifecycle tracking ---
        self.tasks_completed: int = 0          # reached remaining_time <= 0
        self.tasks_fault_terminated: int = 0   # permanently failed (no recovery)
        self.tasks_deadline_missed: int = 0    # time > deadline at completion
        self.tasks_started: int = 0            # total tasks that ever ran

        # Per-task timing (tid -> value)
        self._task_arrival: Dict[int, int] = {}     # time task first arrived
        self._task_start: Dict[int, int] = {}       # time task first got CPU
        self._task_finish: Dict[int, int] = {}      # time task completed/terminated
        self._task_waiting: Dict[int, int] = defaultdict(int)  # accumulated wait

        # --- CPU accounting ---
        self._idle_steps: int = 0
        self._busy_steps: int = 0

        # --- Energy ---
        self.energy_consumed: float = 0.0

        # --- Context switches ---
        self.context_switches: int = 0

        # --- AI Advisor ---
        self.ai_interventions: int = 0
        self._ai_correct_predictions: int = 0   # intervention preceded a fault
        self._ai_total_predictions: int = 0

        # --- Fault breakdown ---
        self.fault_counts: Dict[str, int] = defaultdict(int)

        # --- Scheduler identity (set externally) ---
        self.scheduler_name: str = "unknown"
        self._start_wall: float = wallclock.time()

    # ------------------------------------------------------------------ #
    #  Per-step recording                                                  #
    # ------------------------------------------------------------------ #

    def record_step(self, data: Dict):
        """Called once per simulation tick with current system state."""
        self.records.append(data)
        if data.get("task_running"):
            self._busy_steps += 1
        else:
            self._idle_steps += 1

    def record_fault(self, fault: Dict):
        """Record a fault event; keys: fault_type, task_id, time."""
        self.faults.append(fault)
        self.fault_counts[fault.get("fault_type", "UNKNOWN")] += 1

    # ------------------------------------------------------------------ #
    #  Task lifecycle events                                               #
    # ------------------------------------------------------------------ #

    def record_task_arrival(self, task_id: int, time: int):
        if task_id not in self._task_arrival:
            self._task_arrival[task_id] = time

    def record_task_started(self, task_id: int, time: int):
        self.tasks_started += 1
        if task_id not in self._task_start:
            self._task_start[task_id] = time

    def record_task_waiting(self, task_id: int, ticks: int = 1):
        self._task_waiting[task_id] += ticks

    def record_task_completed(self, task_id: int, time: int, missed_deadline: bool):
        self.tasks_completed += 1
        self._task_finish[task_id] = time
        if missed_deadline:
            self.tasks_deadline_missed += 1

    def record_task_fault_terminated(self, task_id: int, time: int):
        self.tasks_fault_terminated += 1
        self._task_finish[task_id] = time

    def record_context_switch(self):
        self.context_switches += 1

    def record_energy(self, amount: float):
        self.energy_consumed += amount

    def record_ai_intervention(self, predicted_fault: bool, actual_fault: bool):
        """Track whether the AI advisor's prediction was correct."""
        self._ai_total_predictions += 1
        if predicted_fault:
            self.ai_interventions += 1
            if actual_fault:
                self._ai_correct_predictions += 1

    # ------------------------------------------------------------------ #
    #  Derived KPIs                                                        #
    # ------------------------------------------------------------------ #

    @property
    def total_tasks(self) -> int:
        return self.tasks_completed + self.tasks_fault_terminated

    @property
    def deadline_miss_rate(self) -> float:
        """Fraction of completed tasks that missed their deadline."""
        if self.tasks_completed == 0:
            return 0.0
        return self.tasks_deadline_missed / self.tasks_completed

    @property
    def task_completion_rate(self) -> float:
        """Fraction of all finished tasks that completed successfully."""
        if self.total_tasks == 0:
            return 0.0
        return self.tasks_completed / self.total_tasks

    @property
    def cpu_utilization(self) -> float:
        """Fraction of simulation steps where CPU was not idle."""
        total = self._busy_steps + self._idle_steps
        if total == 0:
            return 0.0
        return self._busy_steps / total

    @property
    def average_waiting_time(self) -> float:
        """Mean accumulated waiting ticks across all tasks that ran."""
        if not self._task_waiting:
            return 0.0
        return sum(self._task_waiting.values()) / len(self._task_waiting)

    @property
    def average_turnaround_time(self) -> float:
        """Mean time from arrival to finish across all completed tasks."""
        turnarounds = []
        for tid, finish in self._task_finish.items():
            arrival = self._task_arrival.get(tid)
            if arrival is not None:
                turnarounds.append(finish - arrival)
        return sum(turnarounds) / len(turnarounds) if turnarounds else 0.0

    @property
    def throughput(self) -> float:
        """Tasks completed per simulation time unit."""
        total_steps = len(self.records)
        if total_steps == 0:
            return 0.0
        return self.tasks_completed / total_steps

    @property
    def fault_rate(self) -> float:
        """Faults per simulation step."""
        if not self.records:
            return 0.0
        return len(self.faults) / len(self.records)

    @property
    def ai_precision(self) -> Optional[float]:
        """Precision of AI interventions (were they followed by actual faults?)."""
        if self.ai_interventions == 0:
            return None
        return self._ai_correct_predictions / self.ai_interventions

    # ------------------------------------------------------------------ #
    #  Output                                                              #
    # ------------------------------------------------------------------ #

    def summary(self):
        """Print a formatted metrics summary to stdout."""
        elapsed = wallclock.time() - self._start_wall
        total = self.total_tasks or 1  # avoid div-by-zero for display

        print("\n" + "═" * 55)
        print(f"  📊  SENTINELOS METRICS  —  Scheduler: {self.scheduler_name.upper()}")
        print("═" * 55)
        print(f"  Simulation steps        : {len(self.records)}")
        print(f"  Wall-clock time         : {elapsed:.2f}s")
        print()
        print("  ── Task Lifecycle ──────────────────────────────")
        print(f"  Tasks completed         : {self.tasks_completed}")
        print(f"  Tasks fault-terminated  : {self.tasks_fault_terminated}")
        print(f"  Completion rate         : {self.task_completion_rate:.1%}")
        print(f"  Deadline miss rate      : {self.deadline_miss_rate:.1%}")
        print(f"  Throughput              : {self.throughput:.4f} tasks/step")
        print()
        print("  ── Scheduling Quality ──────────────────────────")
        print(f"  CPU utilization         : {self.cpu_utilization:.1%}")
        print(f"  Avg waiting time        : {self.average_waiting_time:.2f} ticks")
        print(f"  Avg turnaround time     : {self.average_turnaround_time:.2f} ticks")
        print(f"  Context switches        : {self.context_switches}")
        print()
        print("  ── Faults ──────────────────────────────────────")
        print(f"  Total faults            : {len(self.faults)}")
        print(f"  Fault rate              : {self.fault_rate:.4f} faults/step")
        for ftype, count in sorted(self.fault_counts.items()):
            print(f"    {ftype:<30}: {count}")
        print()
        print("  ── Energy & AI ─────────────────────────────────")
        print(f"  Energy consumed         : {self.energy_consumed:.2f} units")
        print(f"  AI interventions        : {self.ai_interventions}")
        if self.ai_precision is not None:
            print(f"  AI intervention precision: {self.ai_precision:.1%}")
        else:
            print(f"  AI intervention precision: N/A (no interventions)")
        print("═" * 55 + "\n")

    def to_dict(self) -> Dict:
        """Export all KPIs as a serialisable dictionary (for JSON export)."""
        return {
            "scheduler": self.scheduler_name,
            "simulation_steps": len(self.records),
            "tasks_completed": self.tasks_completed,
            "tasks_fault_terminated": self.tasks_fault_terminated,
            "task_completion_rate": round(self.task_completion_rate, 4),
            "deadline_miss_rate": round(self.deadline_miss_rate, 4),
            "throughput": round(self.throughput, 6),
            "cpu_utilization": round(self.cpu_utilization, 4),
            "average_waiting_time": round(self.average_waiting_time, 4),
            "average_turnaround_time": round(self.average_turnaround_time, 4),
            "context_switches": self.context_switches,
            "total_faults": len(self.faults),
            "fault_rate": round(self.fault_rate, 6),
            "fault_breakdown": dict(self.fault_counts),
            "energy_consumed": round(self.energy_consumed, 4),
            "ai_interventions": self.ai_interventions,
            "ai_precision": round(self.ai_precision, 4) if self.ai_precision is not None else None,
        }

    def export_json(self, path: str):
        """Write KPI dict to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        print(f"  ✅ Metrics exported → {path}")